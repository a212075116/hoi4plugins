import os
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
os.makedirs(os.path.join(ROOT, 'localisation', 'english'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'localisation', 'simp_chinese'), exist_ok=True)

en = 'l_english:\n EFFECT_SET_CAMERA_HEIGHT: "Set camera height."\n\n'
cn = 'l_simp_chinese:\n EFFECT_SET_CAMERA_HEIGHT: "\u8bbe\u7f6e\u6444\u50cf\u673a\u9ad8\u5ea6\u3002"\n\n'

for path, text in [(os.path.join(ROOT,'localisation','english','zz_camtest_l_english.yml'), en),
                   (os.path.join(ROOT,'localisation','simp_chinese','zz_camtest_l_simp_chinese.yml'), cn)]:
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(text.encode('utf-8'))
    b = open(path,'rb').read(6)
    print('%-60s BOM=%s' % (os.path.relpath(path, ROOT), b[:3]==b'\xef\xbb\xbf'))

old = os.path.join(ROOT, 'localisation', 'zz_camtest_l_english.yml')
if os.path.exists(old):
    os.remove(old)
    print('已删除旧位置 localisation/zz_camtest_l_english.yml')
