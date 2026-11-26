"""数据源可配置功能回归测试：测试连接端点 + 环境变量切换 Provider/路径。"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "http://127.0.0.1:5288"
API = "http://127.0.0.1:5281"
DLL = ROOT / "SqlPlayground" / "bin" / "Debug" / "net10.0" / "SqlPlayground.dll"
ALT_DB = ROOT / "tests" / "alt.db"


def req(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data,
                               headers={"Content-Type": "application/json"}, method="POST" if data else "GET")
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    print("[1] 测试连接 - SQLite 正确路径")
    r = req(BASE + "/api/connection/test", {"config": json.dumps({"provider": "sqlite", "sqlitePath": "wms.db"})})
    assert r["success"] and r["data"]["ok"] and r["data"]["provider"] == "sqlite", r
    print("    ", r["data"]["target"], r["data"]["version"], f'{r["data"]["elapsedMs"]}ms')

    print("[2] 测试连接 - 不存在的文件应失败")
    r = req(BASE + "/api/connection/test", {"config": json.dumps({"provider": "sqlite", "sqlitePath": "no-such.db"})})
    assert not r["success"] and r["error"]["code"] == "CONNECTION_FAILED", r
    print("    ", r["error"]["message"])

    print("[3] 测试连接 - MySQL 端口不可达应友好失败")
    r = req(BASE + "/api/connection/test", {
        "config": json.dumps({"provider": "mysql", "host": "127.0.0.1", "port": 3306,
                              "database": "test", "user": "root"}), "password": "x"})
    assert not r["success"] and r["error"]["code"] == "CONNECTION_FAILED", r
    print("    ", r["error"]["message"])

    print("[4] 环境变量切换 - 用备用库启动独立后端")
    env = dict(os.environ)
    env["API_URL"] = API
    env["SQL_DB_CONFIG"] = json.dumps({"provider": "sqlite", "sqlitePath": str(ALT_DB)})
    log = open(ROOT / "logs" / "alt-instance.log", "w", encoding="utf-8")
    proc = subprocess.Popen(["dotnet", str(DLL)], cwd=str(ROOT / "SqlPlayground"),
                            env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(40):
            try:
                h = req(API + "/api/health")
                if h["success"]:
                    break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("备用后端未就绪")
        assert h["data"]["db"] == "alt.db" and h["data"]["target"] == "SQLite · alt.db", h
        print("    ", h["data"]["target"])

        print("[5] 备用库的表结构与查询")
        t = req(API + "/api/tables")
        assert [x["name"] for x in t["data"]["tables"]] == ["alt_table"], t
        q = req(API + "/api/query", {"sql": "SELECT * FROM alt_table"})
        assert q["data"]["rows"] == [[1, "ALPHA"], [2, "BETA"]], q
        print("    ", q["data"]["rows"])

        print("[6] 主实例不受影响（仍用 wms.db）")
        mh = req(BASE + "/api/health")
        assert mh["data"]["db"] == "wms.db", mh
        print("    ", mh["data"]["target"])
    finally:
        try:
            req(API + "/_internal/shutdown")
        except Exception:
            pass
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

    print("数据源配置功能全部验证通过")


if __name__ == "__main__":
    main()
