import io, sys
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/flirt/loader/carrier_loader.cpp'
s = io.open(p, encoding='utf-8').read()
for i, ln in enumerate(s.split('\n'), 1):
    if any(ord(c) > 127 for c in ln):
        print('%4d| %s' % (i, ln))
