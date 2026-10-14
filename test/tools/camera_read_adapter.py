import argparse
import json
import pathlib
import sys

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'modules/camera'))
from camera_read_adapter_core import AdapterError, CameraReader, ImageBindings, ProcessMemory

parser = argparse.ArgumentParser()
parser.add_argument('--image',type=pathlib.Path,required=True)
parser.add_argument('--pid',type=int)
parser.add_argument('--output',type=pathlib.Path,required=True)
args = parser.parse_args()
record = {'writes':False}
try:
    bindings = ImageBindings(args.image)
    record['bindings'] = bindings.describe()
    if args.pid is not None:
        bindings.require_runtime()
        with ProcessMemory(args.pid,args.image) as memory:
            record['snapshot'] = CameraReader(bindings,memory).snapshot()
    record['exit'] = 0
except AdapterError as e:
    record.update(status=e.code,detail=e.detail,exit=2)
except (OSError,ValueError) as e:
    record.update(status='INPUT_ERROR',detail=str(e),exit=2)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
raise SystemExit(record['exit'])
