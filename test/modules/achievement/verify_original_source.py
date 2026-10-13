import hashlib
import io
import json
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPORT = ROOT / "test/reports/20261013_achievement_source"
HEADER = ROOT / "src/plugin/SDK_RVA/achievement/achievement_source.h"
REPORT.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include <stdlib.h>
#include "HEADER"
int main(int argc, char** argv) {
    int passed = 0, total = 0;
    unsigned char bytes[] = {0,1,2,255,128,0,17};
    unsigned char packed[512]; size_t size;
    FILE* f;
#define CHECK(x) do { ++total; if (x) ++passed; else printf("FAIL line=%d\n", __LINE__); } while(0)
    CHECK(AchievementSource_ShouldRedirect(1, ACH_SOURCE_NAME, strlen(ACH_SOURCE_NAME)));
    CHECK(AchievementSource_ShouldRedirect(2, ACH_SOURCE_NAME, strlen(ACH_SOURCE_NAME)));
    CHECK(!AchievementSource_ShouldRedirect(0, ACH_SOURCE_NAME, strlen(ACH_SOURCE_NAME)));
    CHECK(!AchievementSource_ShouldRedirect(-1, ACH_SOURCE_NAME, strlen(ACH_SOURCE_NAME)));
    CHECK(!AchievementSource_ShouldRedirect(1, NULL, 22));
    CHECK(!AchievementSource_ShouldRedirect(1, ACH_SOURCE_NAME, 21));
    CHECK(!AchievementSource_ShouldRedirect(1, "common/achievements.txt/x", 24));
    CHECK(!AchievementSource_ShouldRedirect(1, "common/achievements_mod/x", 24));
    CHECK(!AchievementSource_ShouldRedirect(1, "common/achievements.txtx", strlen("common/achievements.txtx")));
    CHECK(AchievementSource_ZipSize(0) == 0);
    CHECK(AchievementSource_ZipSize(ACH_SOURCE_MAX_BYTES + 1) == 0);
    CHECK(AchievementSource_ZipSize(ACH_SOURCE_MAX_BYTES) > ACH_SOURCE_MAX_BYTES);
    CHECK(AchievementSource_Pack(bytes, sizeof(bytes), packed, 1) == 0);
    CHECK(AchievementSource_Pack(NULL, sizeof(bytes), packed, sizeof(packed)) == 0);
    CHECK(AchievementSource_Pack(bytes, sizeof(bytes), NULL, sizeof(packed)) == 0);
    size = AchievementSource_Pack(bytes, sizeof(bytes), packed, sizeof(packed));
    CHECK(size == AchievementSource_ZipSize(sizeof(bytes)));
    if (argc != 2 || !(f = fopen(argv[1], "wb"))) return 3;
    fwrite(packed, 1, size, f); fclose(f);
    printf("%d/%d source policy and bounds; no game or Steam calls\n", passed, total);
    return passed == total ? 0 : 1;
}
'''.replace("HEADER", HEADER.as_posix())
cpp = REPORT / "source_contract.c"
cpp.write_text(source, encoding="utf-8")
exe = REPORT / "source_contract.exe"
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
compile_command = f'"{vc}" >nul && cl /nologo /TC /MT "{cpp}" /Fe:"{exe}" /Fo:"{REPORT / "source_contract.obj"}"'


def run(command):
    result = subprocess.run(command, capture_output=True)
    return {"command": command, "stdout": result.stdout.decode("utf-8", errors="replace"), "stderr": result.stderr.decode("utf-8", errors="replace"), "exit": result.returncode}


build = run('cmd /d /s /c "' + compile_command + '"')
result = run([str(exe), str(REPORT / "packed_fixture.zip")]) if build["exit"] == 0 else build
assert result["exit"] == 0, result
with zipfile.ZipFile(REPORT / "packed_fixture.zip") as archive:
    assert archive.namelist() == ["common/achievements.txt"]
    assert archive.testzip() is None
    assert archive.read("common/achievements.txt") == bytes([0, 1, 2, 255, 128, 0, 17])
record = {"build": build, "result": result, "zip_crc_roundtrip": True, "header_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(), "scope": "Compiled production header, no native eligibility or Steam unlock test"}
(REPORT / "source_contract.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
