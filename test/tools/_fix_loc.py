import os
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
en = 'l_english:\n EFFECT_SET_CAMERA_HEIGHT: "Set camera height: $VAL$"\n\n'
cn = 'l_simp_chinese:\n EFFECT_SET_CAMERA_HEIGHT: "\u8bbe\u7f6e\u6444\u50cf\u673a\u9ad8\u5ea6\uff1a$VAL$\u3002"\n\n'
for path, text in [(os.path.join(ROOT,'localisation','english','zz_camtest_l_english.yml'), en),
                   (os.path.join(ROOT,'localisation','simp_chinese','zz_camtest_l_simp_chinese.yml'), cn)]:
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf'); f.write(text.encode('utf-8'))
    print('written ' + os.path.basename(path))
