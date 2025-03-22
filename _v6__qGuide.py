#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ------------------------------------------------
# COPYRIGHT (C) 2014-2025 Mitsuo KONDOU.
# This software is released under the MIT License.
# https://github.com/konsan1101
# Thank you for keeping the rules.
# ------------------------------------------------

import os
import time
import io

import queue

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk

import numpy as np
import cv2

if (os.name == 'nt'):
    import win32clipboard



# インターフェース
qPath_fonts  = '_fonts/'
qPath_icons  = '_icons/'

# 共通ルーチン
import   _v6__qGUI
qGUI   = _v6__qGUI.qGUI_class()



class qGuide_class:

    def __init__(self, ):
        self.screen         = '0'
        self.panel          = '5-'

        self.img_file       = '_icons/RiKi_start.png'

        titlex              = os.path.basename(__file__)
        self.title          = titlex.replace('.py','')

        self.theme          = 'Dark' # 'Default1', 'Dark',
        self.alpha_channel  = 1.0
        self.icon           = None
        self.font           = ('Arial', 8)

        self.keep_on_top    = True
        self.no_titlebar    = True
        self.disable_close  = True
        self.resizable      = False
        self.no_border      = True

        self.window         = None
        self.left           = 0
        self.top            = 0
        self.width          = 320
        self.height         = 240

        # tkinter
        self.image_label        = None
        self.event_queue        = queue.Queue()
        self.tk_image           = None
        self.default_img        = None
        self.last_resize_w      = 0
        self.last_resize_h      = 0

        # フォント
        self.font_default = {'file':qPath_fonts + '_vision_font_ipaexg.ttf','offset':8}
        self.font_status  = {'file':qPath_fonts + '_vision_font_ipag.ttf',  'offset':8}
        try:
            self.font32_default  = ImageFont.truetype(self.font_default['file'], 32, encoding='unic')
            self.font32_defaulty =                    self.font_default['offset']
        except:
            self.font32_default  = None
            self.font32_defaulty = 0

    def init(self,
             screen='auto', panel='auto',
             title='', image=None, theme=None,
             keep_on_top='yes', alpha_channel='1', icon=None, ):

        # スクリーン
        if (str(screen) != 'auto'):
            try:
                self.screen = int(screen)
            except Exception as e:
                print(e)

        # パネル
        if (panel != 'auto'):
            self.panel = panel

        # タイトル
        if (title != ''):
            self.title  = title
        else:
            titlex      = os.path.basename(__file__)
            titlex      = titlex.replace('.py','')

        # イメージセット
        self.image = None
        if (image is not None):
            self.image = image
            self.default_img = image

        # テーマ
        if (theme is not None):
            self.theme = theme
        #sg.theme(self.theme)
        # ボーダー
        if (self.no_border != True):
            self.element_padding= ((2,2),(2,2)) #((left/right),(top/bottom))
        else:
            self.element_padding= ((0,0),(0,0)) #((left/right),(top/bottom))
            #sg.set_options(element_padding=(0,0), margins=(0,0), border_width=0)

        # 最前面
        if (keep_on_top != 'no'):
            self.keep_on_top = True
        else:
            self.keep_on_top = False

        # 透過表示
        if (str(alpha_channel) != ''):
            try:
                self.alpha_channel = float(alpha_channel)
            except Exception as e:
                print(e)

        # アイコン
        if (icon is not None):
            self.icon = icon

        # 表示位置
        qGUI.checkUpdateScreenInfo(update=True, )
        self.left, self.top, self.width, self.height = qGUI.getScreenPanelPosSize(screen=self.screen, panel=self.panel, )

        # ウィンドウ設定
        if self.window is not None:
            self.terminate()
        try:
            self.window = tk.Tk()
            self.window.attributes("-alpha", 0)
            self.window.update_idletasks()
            self.window.title(self.title)

            if icon is not None and os.path.isfile(icon):
                self.window.iconbitmap(icon)

            geometry_str = f"{self.width}x{self.height}{self.left :+}{self.top :+}"
            self.window.geometry(geometry_str)
            self.window.wm_attributes("-topmost", True if keep_on_top != 'no' else False)
            self.window.resizable(self.resizable, self.resizable)
            if self.no_titlebar:
                self.window.overrideredirect(True)
            self.image_label = tk.Label(self.window)
            self.image_label.pack(fill="both", expand=True)
            self.image_label.bind("<Button-1>", self.handle_img_click)
            self.window.protocol("WM_DELETE_WINDOW", self.on_close)
            if (self.image is None):
                self.default_img = np.zeros((self.height, self.width, 3), np.uint8)
                cv2.rectangle(self.default_img, (0, 0), (self.width, self.height), (255, 0, 0), -1)
            self.window.geometry(geometry_str)
            self.window.attributes("-alpha", self.alpha_channel)
            self.reset()
        except Exception as e:
            print(e)
            self.window = None

        if (self.window is not None):
            return True
        else:
            return False

    def handle_img_click(self, event):
        self.event_queue.put("_output_img_")

    def on_close(self):
        self.event_queue.put("WIN_CLOSED")
        self.terminate()

    def open(self, refresh=True):
        # 更新・表示
        try:
            if self.window is not None:
                self.window.deiconify()
                if refresh:
                    self.refresh()
                return True
        except Exception as e:
            print(e)
        return False

    def read(self, timeout=20, timeout_key='-idoling-', ):
        # 読取
        try:
            start_time = time.time()
            while (time.time() - start_time) * 1000 < timeout:
                try:
                    event = self.event_queue.get_nowait()
                    return event, {}
                except queue.Empty:
                    pass
                self.window.update()
                time.sleep(0.01)
            return timeout_key, {}
        except Exception as e:
            print(e)
        return False, False

    def close(self, ):
        # 消去
        if (self.window is not None):
            try:
                self.window.withdraw()
                self.window.update()
            except Exception as e:
                print(e)
        return True

    def terminate(self, ):
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception as e:
                print(e)
        self.window = None
        return True

    # GUI 画面リセット
    def reset(self):
        try:
            w = self.window.winfo_width()
            h = self.window.winfo_height()
        except:
            return False

        ## 規定値(イメージ)
        #self.default_img = np.zeros((240, 320, 3), np.uint8)
        #cv2.rectangle(self.default_img,(0,0),(320,240),(255,0,0),-1)
        #try:
        #    if (os.path.isfile(self.img_file)):
        #        self.default_img = cv2.imread(self.img_file)
        #except:
        #    pass

        # 項目リセット
        self.setImage(self.default_img, refresh=False)
        return True

    # GUI 画面リサイズ
    def resize(self, reset=False, ):
        try:
            w = self.window.winfo_width()
            h = self.window.winfo_height()
        except:
            return False

        # リセット
        if (reset == True):
            self.last_resize_w, self.last_resize_h = 0, 0

        # 画面リサイズ？
        if (w != self.last_resize_w) or (h != self.last_resize_h):
            self.last_resize_w, self.last_resize_h = w, h

            # 項目リセット
            self.setImage(self.default_img, refresh=True)

        return True

    # GUI 画面更新
    def refresh(self):
        try:
            self.window.update_idletasks()
            return True
        except Exception as e:
            print(e)
        return False    

    # 画像セット
    def setImage(self, image=None, refresh=True, ):
        try:
            w = self.window.winfo_width()
            h = self.window.winfo_height()
        except:
            return False

        if (image is None):
            img = np.zeros((h, w, 3), np.uint8)
        else:
            img = cv2.resize(image, (w, h))

        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img_rgb)
            self.tk_image = ImageTk.PhotoImage(im)
            self.image_label.config(image=self.tk_image)
            if refresh:
                self.refresh()
            return True
        except Exception as e:
            print(e)
        return False

    # アルファチェンネル
    def setAlphaChannel(self, alpha_channel=1, ):
        try:
            self.window.attributes("-alpha", alpha_channel)
        except:
            pass

    # フェードアウト（フェード開始）
    def fadeOut(self, screen=0, panel='0', mask='black', outSec=2, ):
        if (mask != 'white'):
            img   = cv2.imread(qPath_icons + '__black.png')
        else:
            img   = cv2.imread(qPath_icons + '__white.png')
        try:
            self.init(screen=screen, panel=panel, title=mask, alpha_channel=0, )
            self.setImage(image=img, )
            self.open()

            alpha = 0
            self.setAlphaChannel(alpha)

            chkTime = time.time()
            while ((time.time() - chkTime) < 5):
                event, values = self.read(timeout=int(outSec*1000/50), )
                if event in (None, '-exit-'):
                    break
                alpha += 0.02
                if (alpha > 1):
                    break
                self.setAlphaChannel(alpha)
                #time.sleep(0.01)
            alpha = 1
            self.setAlphaChannel(alpha)
            return True
        except Exception as e:
            print(e)
        return False

    # フェードイン（フェード終了）
    def fadeIn(self, inSec=1, ):
        try:
            alpha = 1
            self.setAlphaChannel(alpha)

            chkTime = time.time()
            while ((time.time() - chkTime) < 5):
                event, values = self.read(timeout=int(inSec*1000/50), )
                if event in (None, '-exit-'):
                    break
                alpha -= 0.02
                if (alpha < 0):
                    break
                self.setAlphaChannel(alpha)
                #time.sleep(0.01)
            alpha = 0
            self.setAlphaChannel(alpha)

            self.close()
            self.terminate()
            return True
        except Exception as e:
            print(e)
        return False

    def setMessage(self, txt='', refresh=True, ):
        if (self.window is not None):
            if (self.image is not None):

                try:
                    img = cv2.resize(self.image, (self.width, self.height))

                    # 文字描写
                    if (txt != ''):
                        if (self.font32_default is None):
                            cv2.putText(img, txt, (5,self.height-15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255,0,255))
                        else:
                            pil_image = self.cv2pil(img)
                            text_draw = ImageDraw.Draw(pil_image)
                            text_draw.text((10, self.height-42), txt, font=self.font32_default, fill=(255,0,255))
                            img = self.pil2cv(pil_image)

                    # 更新
                    self.setImage(img, refresh=refresh)
                    return True

                except:
                    pass

        return False

    def cv2pil(self, cv2_image=None):
        try:
            wrk_image = cv2_image.copy()
            if (wrk_image.ndim == 2):  # モノクロ
                pass
            elif (wrk_image.shape[2] == 3):  # カラー
                wrk_image = cv2.cvtColor(wrk_image, cv2.COLOR_BGR2RGB)
            elif (wrk_image.shape[2] == 4):  # 透過
                wrk_image = cv2.cvtColor(wrk_image, cv2.COLOR_BGRA2RGBA)
            pil_image = Image.fromarray(wrk_image)
            return pil_image
        except:
            pass
        return None

    def pil2cv(self, pil_image=None):
        try:
            cv2_image = np.array(pil_image, dtype=np.uint8)
            if (cv2_image.ndim == 2):  # モノクロ
                pass
            elif (cv2_image.shape[2] == 3):  # カラー
                cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_RGB2BGR)
            elif (cv2_image.shape[2] == 4):  # 透過
                cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_RGBA2BGRA)
            return cv2_image
        except:
            pass
        return None

    def img2clip(self, file):
        if (os.name == 'nt'):
            #try:
                img = Image.open(file)
                output = io.BytesIO()
                img.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]
                output.close()

                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                return True
            #except Exception as e:
            #    pass
        return False

    def getIconImage(self, filename='', ):
        if (filename != ''):
            imgfile = filename
            if (filename == '_kernel_start_'):
                imgfile = qPath_icons + 'RiKi_start.png'
            if (filename == '_kernel_stop_'):
                imgfile = qPath_icons + 'RiKi_stop.png'
            if (filename == '_kernel_guide_'):
                imgfile = qPath_icons + 'RiKi_guide.png'
            if (filename == '_speech_start_'):
                imgfile = qPath_icons + 'speech_start.png'
            if (filename == '_speech_stop_'):
                imgfile = qPath_icons + 'speech_stop.png'
            if (filename == '_speech_guide_'):
                imgfile = qPath_icons + 'speech_guide.png'
            if (filename == '_vision_start_'):
                imgfile = qPath_icons + 'cam_start.png'
            if (filename == '_vision_stop_'):
                imgfile = qPath_icons + 'cam_stop.png'
            if (filename == '_vision_guide_'):
                imgfile = qPath_icons + 'cam_guide.png'
            if (filename == '_desktop_start_'):
                imgfile = qPath_icons + 'rec_start.png'
            if (filename == '_desktop_stop_'):
                imgfile = qPath_icons + 'rec_stop.png'
            if (filename == '_desktop_guide_'):
                imgfile = qPath_icons + 'rec_guide.png'
            try:
                image = cv2.imread(imgfile)
                return image
            except Exception as e:
                pass
        return None



if __name__ == '__main__':

    qGuide = qGuide_class()

    if (True):
        res=qGuide.fadeOut(screen=0, panel='0', mask='black', outSec=2, )
        res=qGuide.fadeIn(inSec=1, )

    if (True):
        img = cv2.imread(qPath_icons + 'RiKi_start.png')
        qGuide.init(screen=0, panel='5', title='', image=img,)
        qGuide.open()
        time.sleep(1.00)
        qGuide.setMessage(txt='開始中．．．', )

        time.sleep(3.00)

        img = cv2.imread(qPath_icons + 'RiKi_stop.png')
        qGuide.setImage(image=img, )
        time.sleep(1.00)
        qGuide.setMessage(txt='終了中．．．', )

        time.sleep(5.00)


    if (True):
        img = cv2.imread(qPath_icons + 'RiKi_base.png')
        qGuide.init(screen=0, panel='5', title='_guide_', image=img,)
        qGuide.setMessage(txt='こんにちは', )
        #qGuide.open()

        chkTime = time.time()
        while ((time.time() - chkTime) < 5):
            event, values = qGuide.read()
            #print(event, values)
            if event in (None, '-exit-'):
                break
        qGuide.close()
        qGuide.terminate()
 


