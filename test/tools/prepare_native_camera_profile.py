import argparse
import hashlib
import pathlib
import sys

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'modules/camera'))
from camera_read_adapter_core import ImageBindings

parser=argparse.ArgumentParser()
parser.add_argument('--image',type=pathlib.Path,required=True)
parser.add_argument('--directory',type=pathlib.Path,default=pathlib.Path('bindings'))
args=parser.parse_args()
b=ImageBindings(args.image)
p=b.profile or {}
approved=bool(p.get('runtime_layout'))
folder=args.directory if approved else args.directory/'candidates'
path=folder/(b.sha+'.profile')
values={'schema':1,'image_sha256':b.sha,'read_contract':'leaf_rtti_v1','camera_pointer':hex(p.get('camera_pointer',0)),
        'height':hex(p.get('height',0)),'minimum':hex(p.get('minimum',0)),'maximum':hex(p.get('maximum',0)),'runtime_read':int(approved)}
text=''.join(str(k)+'='+str(v)+'\n' for k,v in values.items()).encode('ascii')
folder.mkdir(parents=True,exist_ok=True)
if path.exists() and path.read_text(encoding='ascii')!=text.decode('ascii'):
    raise SystemExit('Refusing to overwrite different profile: '+str(path.resolve()))
if not path.exists():path.write_bytes(text)
assert path.read_text(encoding='ascii')==text.decode('ascii')
print('profile='+str(path.resolve())+' sha256='+hashlib.sha256(path.read_bytes()).hexdigest()+' runtime_read='+str(int(approved)))
