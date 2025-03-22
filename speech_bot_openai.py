#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ------------------------------------------------
# COPYRIGHT (C) 2014-2025 Mitsuo KONDOU.
# This software is released under the not MIT License.
# Permission from the right holder is required for use.
# https://github.com/konsan1101
# Thank you for keeping the rules.
# ------------------------------------------------

import sys
import os
import time
import datetime
import codecs
import shutil

import json
import queue
import base64
import glob

import socket
qHOSTNAME = socket.gethostname().lower()



# openai チャットボット
import openai

from typing_extensions import override
from openai import AssistantEventHandler
from openai.types.beta import AssistantStreamEvent
#from openai.types.beta.threads import Message
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta, RunStep

import tiktoken

import speech_bot_openai_key  as openai_key



qPath_temp           = 'temp/'
qPath_output         = 'temp/output/'
qPath_chat_work      = 'temp/chat_work/'



# base64 encode
def base64_encode(file_path):
    with open(file_path, "rb") as input_file:
        return base64.b64encode(input_file.read()).decode('utf-8')



class my_eventHandler(AssistantEventHandler):

    def __init__(self, log_queue=None, my_seq=1, 
                 auto_continue=3, max_step=10,
                 my_client=None,
                 my_assistant_id='', my_assistant_name='',
                 my_thread_id='', 
                 session_id='admin', res_history=[], function_modules={}, 
                 res_text='', res_path='', res_files=[], 
                 upload_files=[], upload_flag=False, ):
        
        super().__init__()

        self.log_queue          = log_queue
        self.my_seq             = my_seq
        self.my_client          = my_client
        self.my_assistant_id    = my_assistant_id
        self.my_assistant_name  = my_assistant_name
        self.my_thread_id       = my_thread_id
        self.auto_continue      = auto_continue
        self.max_step           = max_step
        self.count_run_step     = 0

        self.my_run_id          = None
        self.my_run_status      = None

        self.session_id         = session_id
        self.res_history        = res_history
        self.function_modules   = function_modules
        self.res_text           = res_text
        self.res_path           = res_path
        self.res_files          = res_files
        self.upload_files       = upload_files
        self.upload_flag        = upload_flag

    def print(self, session_id='admin', text='', ):
        print(text, flush=True)
        if (session_id == 'admin') and (self.log_queue is not None):
            try:
                self.log_queue.put(['chatBot', text + '\n'])
            except:
                pass

    def stream(self, session_id='admin', text='', ):
        print(text, end='', flush=True)
        if (session_id == 'admin') and (self.log_queue is not None):
            try:
                self.log_queue.put(['chatBot', text])
            except:
                pass

    # ↓ helpers情報
    # https://github.com/openai/openai-python/blob/main/helpers.md

    @override 
    def on_event ( self, event: AssistantStreamEvent ) -> None : 
        if  (event.event != 'thread.message.delta') \
        and (event.event != 'thread.run.step.delta'):
            if (event.event == 'thread.message.completed'):
                self.print(self.session_id, '\n') 
            self.print(self.session_id, f" Assistant : { event.event }") 

        if (event.event == 'thread.run.step.created'):
            self.count_run_step += 1

            # 最大ステップ  10step x (3auto+1) / 2 = 20
            limit_step = int((int(self.max_step) * (int(self.auto_continue)+1)) / 2)

            if (self.count_run_step > limit_step):
                if (self.my_run_id is not None):
                    self.print(self.session_id, f" Assistant : overstep! (n={ self.count_run_step }!)")
                    try:
                        self.print(self.session_id, f" Assistant : run cancel ... { self.my_run_id }")
                        run = self.my_client.beta.threads.runs.cancel(
                            thread_id = self.my_thread_id, 
                            run_id    = self.my_run_id, )
                        #self.my_run_id = None
                    except Exception as e:
                        print(e)

    @override
    def on_text_created(self, text) -> None:
        self.print(self.session_id, )
        
    @override
    def on_text_delta(self, delta, snapshot):
        if (delta.value is not None):
            if (delta.value != '\n'):
                self.stream(self.session_id, f"{ delta.value }")
            else:
                if (self.res_text[-1] != '\n'):
                    self.stream(self.session_id, f"{ delta.value }")
            self.res_text += str(delta.value)

    @override
    def on_text_done(self, text):
        if (self.res_text[-1] != '\n'):
            self.stream(self.session_id, '\n')
            self.res_text += '\n'

    @override
    def on_image_file_done(self, ImageFile):
        print('on_image_file_done !', ImageFile)

    @override
    def on_message_done(self, Message):
        # ファイル受信
        for c in range(len(Message.content)):
            content_type = Message.content[c].type

            if (content_type == 'text'):
                for a in range(len(Message.content[c].text.annotations)):
                    try:
                        file_type = Message.content[c].text.annotations[a].type
                        file_text = Message.content[c].text.annotations[a].text
                        file_id   = Message.content[c].text.annotations[a].file_path.file_id

                        file_dic  = self.my_client.files.retrieve(file_id)
                        filename = os.path.basename(file_dic.filename)
                        content_file = self.my_client.files.content(file_id)
                        data_bytes   = content_file.read()
                        with open(qPath_output + filename, "wb") as file:
                            file.write(data_bytes)

                        self.res_path = qPath_output + filename
                        self.print(self.session_id, f" Assistant : Download ... { file_text }")
                    except Exception as e:
                        #print(e)
                        pass

    @override
    def on_end(self, ):
        try:
            run = self.my_client.beta.threads.runs.retrieve(
                thread_id=self.my_thread_id,
                run_id=self.my_run_id, )
            self.my_run_status = run.status
        except:
            self.my_run_status = None

    @override
    def on_run_step_created(self, run_step: RunStep) -> None:
        self.my_run_id = run_step.run_id

    @override
    def on_tool_call_created(self, tool_call):
        if tool_call.type == 'code_interpreter':
            self.print(self.session_id, f" Assistant : { tool_call.type }")
        self.print(self.session_id, )

    def on_tool_call_delta(self, delta, snapshot): 
        if delta.type == 'code_interpreter':
            #print(f"on_tool_call_delta > code_interpreter")
            if delta.code_interpreter.input:
                print(str(delta.code_interpreter.input), end="", flush=True)
            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        self.print(self.session_id, f"\n{ output.logs }")
          
    @override
    def on_tool_call_done(self, tool_call: ToolCall) -> None:       
        run = self.my_client.beta.threads.runs.retrieve(
            thread_id=self.my_thread_id,
            run_id=self.my_run_id, )
        if run.status == "completed":
            return
        
        elif run.status == "requires_action":
            tool_result = []
            #tool_call_id   = tool_call.id
            #function_name  = tool_call.function.name
            #json_kwargs    = tool_call.function.arguments

            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            for t in range(len(tool_calls)):
                tool_call_id  = tool_calls[t].id
                function_name = tool_calls[t].function.name
                json_kwargs   = tool_calls[t].function.arguments

                hit = False
                for module_dic in self.function_modules.values():
                    if (function_name == module_dic['func_name']):
                        hit = True
                        self.print(self.session_id, f" Assistant :   function_call '{ module_dic['script'] }' ({  function_name })")
                        self.print(self.session_id, f" Assistant :   → { json_kwargs }")

                        # メッセージ追加格納
                        self.my_seq += 1
                        dic = {'seq': self.my_seq, 'time': time.time(), 'role': 'function_call', 'name': function_name, 'content': json_kwargs }
                        self.res_history.append(dic)

                        # function 実行
                        try:
                            ext_func_proc  = module_dic['func_proc']
                            res_json       = ext_func_proc( json_kwargs )
                        except Exception as e:
                            print(e)
                            # エラーメッセージ
                            dic = {}
                            dic['error'] = e 
                            res_json = json.dumps(dic, ensure_ascii=False, )

                        # メッセージ追加格納
                        self.my_seq += 1
                        dic = {'seq': self.my_seq, 'time': time.time(), 'role': 'function', 'name': function_name, 'content': res_json }
                        self.res_history.append(dic)

                        # パス情報確認
                        try:
                            dic  = json.loads(res_json)
                            path = dic.get('image_path')
                            if (path is None):
                                path = dic.get('excel_path')
                            if (path is not None):
                                self.res_path = path
                                self.res_files.append(path)
                                self.upload_files.append(path)
                                self.res_files    = list(set(self.res_files))
                                self.upload_files = list(set(self.upload_files))

                                # ファイルアップロード
                                upload_ids = self.threadFile_set(session_id     = self.session_id,
                                                                 upload_files   = self.upload_files,
                                                                 assistant_id   = self.my_assistant_id,
                                                                 assistant_name = self.my_assistant_name, )
                                self.upload_flag = True

                        except Exception as e:
                            print(e)

                if (hit == False):
                    self.print(self.session_id, f" Assistant :   function_call Error ! ({ function_name })")
                    self.print(self.session_id, json_kwargs, )

                    dic = {}
                    dic['result'] = 'error' 
                    res_json = json.dumps(dic, ensure_ascii=False, )

                # tool_result
                self.print(self.session_id, f" Assistant :   → { res_json }")
                self.print(self.session_id, '')
                tool_result.append({"tool_call_id": tool_call_id, "output": res_json})

            # 結果通知
            my_handler = my_eventHandler(log_queue=self.log_queue, my_seq=self.my_seq, 
                                         auto_continue=self.auto_continue, max_step=self.max_step,
                                         my_client=self.my_client,
                                         my_assistant_id=self.my_assistant_id, my_assistant_name=self.my_assistant_name, 
                                         my_thread_id=self.my_thread_id,
                                         session_id=self.session_id, res_history=self.res_history, function_modules=self.function_modules,
                                         res_text=self.res_text, res_path=self.res_path, res_files=self.res_files, 
                                         upload_files=self.upload_files, upload_flag=self.upload_flag, )
            with self.my_client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=self.my_thread_id,
                run_id=self.my_run_id,
                tool_outputs=tool_result,
                event_handler=my_handler,
                #stream=True,
            ) as stream:
                stream.until_done()
            self.my_seq       = my_handler.my_seq
            self.res_history  = my_handler.res_history
            self.res_text     = my_handler.res_text
            self.res_path     = my_handler.res_path
            self.res_files    = my_handler.res_files
            self.upload_files = my_handler.upload_files
            self.upload_flag  = my_handler.upload_flag

    def threadFile_set(self, session_id='admin', upload_files=[], assistant_id=None, assistant_name='', ):
        upload_ids = []

        # # 2024/04/21時点 azure 未対応
        # if (self.openai_api_type == 'azure'):
        #    return upload_ids

        for upload_file in upload_files:
            base_name   = os.path.basename(upload_file)
            work_name   = assistant_name + '_' + base_name
            upload_work = qPath_chat_work + work_name
            shutil.copy(upload_file, upload_work)

            # 既に存在なら、置換えの為、削除
            assistant_files_list = self.my_client.files.list()
            for f in range(len(assistant_files_list.data)):
                file_id   = assistant_files_list.data[f].id
                file_name = assistant_files_list.data[f].filename
                if (file_name == work_name):
                    res = self.my_client.files.delete(
                        file_id=file_id, )

            # アップロード
            upload = self.my_client.files.create(
                file = open(upload_work, 'rb'),
                purpose='assistants', )
            upload_ids.append(upload.id)

            self.print(session_id, f" Assistant : Upload ... { upload.id }, { base_name },")

            # proc? wait
            #time.sleep(0.50)

        return upload_ids



class ChatBotAPI:

    def __init__(self, ):
        self.log_queue              = None

        self.bot_auth               = None
        self.default_gpt            = 'auto'
        self.default_class          = 'auto'
        self.auto_continue          = 3
        self.max_step               = 10
        self.max_session            = 5

        self.client_ab              = None
        self.client_v               = None
        self.client_x               = None

        self.assistant_name         = qHOSTNAME
        self.assistant_id           = {}
        self.thread_id              = {}

        self.temperature            = 0.8
        self.timeOut                = 120
        
        self.openai_api_type        = None
        self.openai_default_gpt     = None
        self.openai_organization    = None
        self.openai_key_id          = None
        self.azure_endpoint         = None
        self.azure_version          = None
        self.azure_key_id           = None

        self.gpt_a_enable           = False
        self.gpt_a_nick_name        = ''
        self.gpt_a_model1           = None
        self.gpt_a_token1           = 0
        self.gpt_a_model2           = None
        self.gpt_a_token2           = 0
        self.gpt_a_model3           = None
        self.gpt_a_token3           = 0

        self.gpt_b_enable           = False
        self.gpt_b_nick_name        = ''
        self.gpt_b_model1           = None
        self.gpt_b_token1           = 0
        self.gpt_b_model2           = None
        self.gpt_b_token2           = 0
        self.gpt_b_model3           = None
        self.gpt_b_token3           = 0

        self.gpt_b_length           = 500

        self.gpt_v_enable           = False
        self.gpt_v_nick_name        = ''
        self.gpt_v_model            = None
        self.gpt_v_token            = 0

        self.gpt_x_enable           = False
        self.gpt_x_nick_name        = ''
        self.gpt_x_model1           = None
        self.gpt_x_token1           = 0
        self.gpt_x_model2           = None
        self.gpt_x_token2           = 0

        self.seq                    = 0
        self.reset()

    def init(self, log_queue=None, ):
        self.log_queue = log_queue
        return True

    def reset(self, ):
        self.history                = []
        self.assistant_id           = {}
        self.thread_id              = {}
        return True

    def print(self, session_id='admin', text='', ):
        print(text, flush=True)
        if (session_id == 'admin') and (self.log_queue is not None):
            try:
                self.log_queue.put(['chatBot', text + '\n'])
            except:
                pass

    def stream(self, session_id='admin', text='', ):
        print(text, end='', flush=True)
        if (session_id == 'admin') and (self.log_queue is not None):
            try:
                self.log_queue.put(['chatBot', text])
            except:
                pass

    def authenticate(self, api,
                     openai_api_type,
                     openai_default_gpt, openai_default_class,
                     openai_auto_continue,
                     openai_max_step, openai_max_session,

                     openai_organization, openai_key_id,
                     azure_endpoint, azure_version, azure_key_id,

                     gpt_a_nick_name, 
                     gpt_a_model1, gpt_a_token1, 
                     gpt_a_model2, gpt_a_token2, 
                     gpt_a_model3, gpt_a_token3,
                     gpt_b_nick_name, 
                     gpt_b_model1, gpt_b_token1, 
                     gpt_b_model2, gpt_b_token2, 
                     gpt_b_model3, gpt_b_token3,
                     gpt_b_length,
                     gpt_v_nick_name, 
                     gpt_v_model, gpt_v_token, 
                     gpt_x_nick_name, 
                     gpt_x_model1, gpt_x_token1, 
                     gpt_x_model2, gpt_x_token2, 
                    ):

        # 設定
        if (not os.path.isdir(qPath_temp)):
            os.mkdir(qPath_temp)
        if (not os.path.isdir(qPath_output)):
            os.mkdir(qPath_output)
        if (not os.path.isdir(qPath_chat_work)):
            os.mkdir(qPath_chat_work)

        # 認証
        self.bot_auth               = None

        self.default_gpt            = openai_default_gpt
        self.default_class          = openai_default_class
        if (str(openai_auto_continue) != 'auto'):
            self.auto_continue      = int(openai_auto_continue)
        if (str(openai_max_step)      != 'auto'):
            self.max_step           = int(openai_max_step)
        if (str(openai_max_session) != 'auto'):
            self.max_session        = int(openai_max_session)

        self.client_ab              = None
        self.client_v               = None
        self.client_x               = None

        my_assistant_name         = qHOSTNAME
        self.assistant_session      = {}

        # openai チャットボット
        if (api == 'chatgpt'):

            self.gpt_a_enable       = False
            #self.gpt_a_nick_name    = gpt_a_nick_name
            self.gpt_a_model1       = gpt_a_model1
            self.gpt_a_token1       = int(gpt_a_token1)
            self.gpt_a_model2       = gpt_a_model2
            self.gpt_a_token2       = int(gpt_a_token2)
            self.gpt_a_model3       = gpt_a_model3
            self.gpt_a_token3       = int(gpt_a_token3)

            self.gpt_b_enable       = False
            #self.gpt_b_nick_name    = gpt_b_nick_name
            self.gpt_b_model1       = gpt_b_model1
            self.gpt_b_token1       = int(gpt_b_token1)
            self.gpt_b_model2       = gpt_b_model2
            self.gpt_b_token2       = int(gpt_b_token2)
            self.gpt_b_model3       = gpt_b_model3
            self.gpt_b_token3       = int(gpt_b_token3)

            self.gpt_b_length       = int(gpt_b_length)

            self.gpt_v_enable       = False
            #self.gpt_v_nick_name    = gpt_v_nick_name
            self.gpt_v_model        = gpt_v_model
            self.gpt_v_token        = int(gpt_v_token)

            self.gpt_x_enable       = False
            #self.gpt_x_nick_name    = gpt_x_nick_name
            self.gpt_x_model1       = gpt_x_model1
            self.gpt_x_token1       = int(gpt_x_token1)
            self.gpt_x_model2       = gpt_x_model2
            self.gpt_x_token2       = int(gpt_x_token2)

            if (openai_api_type == 'openai'):
                self.openai_key_id  = openai_key_id
                if (openai_key_id[:1] == '<'):
                    return False
                try:
                    self.openai_api_type = openai_api_type
                    self.client_ab = openai.OpenAI(
                        organization=openai_organization,
                        api_key=openai_key_id,
                    )
                    self.client_v  = openai.OpenAI(
                        organization=openai_organization,
                        api_key=openai_key_id,
                    )
                    self.client_x  = openai.OpenAI(
                        organization=openai_organization,
                        api_key=openai_key_id,
                    )
                except Exception as e:
                    print(e)
                    return False

                try:
                    res = self.client_ab.models.list()
                    for model in res:
                        if (model.id == gpt_a_model1):
                            if (self.gpt_a_token1 > 0):
                                self.bot_auth        = True
                                self.gpt_a_enable    = True
                                self.gpt_a_nick_name = gpt_a_nick_name
                        if (model.id == gpt_b_model1):
                            if (self.gpt_b_token1 > 0):
                                self.bot_auth        = True
                                self.gpt_b_enable    = True
                                self.gpt_b_nick_name = gpt_b_nick_name
                        if (model.id == gpt_v_model):
                            if (self.gpt_v_token > 0):
                                self.bot_auth        = True
                                self.gpt_v_enable    = True
                                self.gpt_v_nick_name = gpt_v_nick_name
                        if (model.id == gpt_x_model1):
                            if (self.gpt_x_token1 > 0):
                                self.bot_auth        = True
                                self.gpt_x_enable    = True
                                self.gpt_x_nick_name = gpt_x_nick_name

                    if (self.bot_auth == True):
                        self.openai_organization = openai_organization
                        self.openai_key_id       = openai_key_id
                        return True

                    print(f"★Model nothing, { gpt_a_model1 }, { gpt_b_model1 },")
                    for dt in res['data']:
                        print(dt['id'])

                    return False

                except Exception as e:
                    print(e)
                    return False

            if (openai_api_type == 'azure'):
                self.azure_key_id = azure_key_id
                if (azure_key_id[:1] == '<'):
                    return False
                try:
                    self.openai_api_type = openai_api_type
                    self.client_ab = openai.AzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_version=azure_version,
                        api_key=azure_key_id,
                    )
                    self.client_v  = openai.AzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_version=azure_version,
                        api_key=azure_key_id,
                    )
                    self.client_x  = openai.AzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_version=azure_version,
                        api_key=azure_key_id,
                    )
                except Exception as e:
                    print(e)
                    return False

                self.azure_endpoint     = azure_endpoint
                self.azure_version      = azure_version
                self.azure_key_id       = azure_key_id

                if (gpt_a_nick_name != '') and (gpt_a_model1 != ''):
                    if (self.gpt_a_token1 > 0):
                        self.bot_auth           = True
                        self.gpt_a_enable       = True
                        self.gpt_a_nick_name    = gpt_a_nick_name

                if (gpt_b_nick_name != '') and (gpt_b_model1 != ''):
                    if (self.gpt_b_token1 > 0):
                        self.bot_auth           = True
                        self.gpt_b_enable       = True
                        self.gpt_b_nick_name    = gpt_b_nick_name

                if (gpt_v_nick_name != '') and (gpt_v_model != ''):
                    if (self.gpt_v_token > 0):
                        self.bot_auth           = True
                        self.gpt_v_enable       = True
                        self.gpt_v_nick_name    = gpt_v_nick_name

                if (gpt_x_nick_name != '') and (gpt_x_model1 != ''):
                    if (self.gpt_x_token1 > 0):
                        self.bot_auth           = True
                        self.gpt_x_enable       = True
                        self.gpt_x_nick_name    = gpt_x_nick_name

                return True

        return False

    def history_add(self, history=[], sysText=None, reqText=None, inpText='こんにちは', ):
        res_history = history

        # sysText, reqText, inpText -> history
        if (sysText is not None) and (sysText.strip() != ''):
            if (len(res_history) > 0):
                if (sysText.strip() != res_history[0]['content'].strip()):
                    res_history = []
            if (len(res_history) == 0):
                self.seq += 1
                dic = {'seq': self.seq, 'time': time.time(), 'role': 'system', 'name': '', 'content': sysText.strip() }
                res_history.append(dic)
        if (reqText is not None) and (reqText.strip() != ''):
            self.seq += 1
            dic = {'seq': self.seq, 'time': time.time(), 'role': 'user', 'name': '', 'content': reqText.strip() }
            res_history.append(dic)
        if (inpText.strip() != ''):
            self.seq += 1
            dic = {'seq': self.seq, 'time': time.time(), 'role': 'user', 'name': '', 'content': inpText.rstrip() }
            res_history.append(dic)

        return res_history

    def history_zip1(self, history=[]):
        res_history = history

        if (len(res_history) > 0):
            for h in reversed(range(len(res_history))):
                tm = res_history[h]['time']
                if ((time.time() - tm) > 900): #15分で忘れてもらう
                    if (h != 0):
                        del res_history[h]
                    else:
                        if (res_history[0]['role'] != 'system'):
                            del res_history[0]

        return res_history

    def history_zip2(self, history=[], leave_count=4, ):
        res_history = history

        if (len(res_history) > 6):
            for h in reversed(range(2, len(res_history) - leave_count)):
                del res_history[h]

        return res_history

    def history2msg_gpt(self, history=[], ):
        res_msg = []
        for h in range(len(history)):
            role    = history[h]['role']
            content = history[h]['content']
            name    = history[h]['name']
            if (role != 'function_call'):
            #if True:
                if (name == ''):
                    dic = {'role': role, 'content': content }
                    res_msg.append(dic)
                else:
                    dic = {'role': role, 'name': name, 'content': content }
                    res_msg.append(dic)

        return res_msg

    def history2msg_vision(self, history=[], image_urls=[], ):
        res_msg = []
        last_h  = 0
        for h in range(len(history)):
            role    = history[h]['role']
            if (role != 'function_call') and (role != 'function'):
                last_h = h 

        for h in range(len(history)):
            role    = history[h]['role']
            content = history[h]['content']
            name    = history[h]['name']
            if (role != 'function_call') and (role != 'function'):
                con = []
                con.append({'type': 'text', 'text': content})
                if (h == last_h):
                    for image_url in image_urls:
                        con.append(image_url)
                if (name == ''):
                    dic = {'role': role, 'content': con }
                    res_msg.append(dic)
                else:
                    dic = {'role': role, 'name': name, 'content': con }
                    res_msg.append(dic)

        return res_msg

    def checkTokens(self, session_id='admin', messages={}, functions=[], model_select='auto', ):
        select = 'a'
        nick_name = self.gpt_a_nick_name
        model     = self.gpt_a_model1
        max       = self.gpt_a_token1
        if (model_select == 'b'):
            if (self.gpt_b_enable == True):
                select = 'b'
                nick_name = self.gpt_b_nick_name
                model     = self.gpt_b_model1
                max       = self.gpt_b_token1
        if (model_select == 'v'):
            if (self.gpt_v_enable == True):
                select = 'v'
                nick_name = self.gpt_v_nick_name
                model     = self.gpt_v_model
                max       = self.gpt_v_token
        if (model_select == 'x'):
            if (self.gpt_x_enable == True):
                select = 'x'
                nick_name = self.gpt_x_nick_name
                model     = self.gpt_x_model1
                max       = self.gpt_x_token1
        len_tokens = 0

        if (select == 'a') or (select == 'b'):

            try:
                add_tokens = 0

                #encoding_model = tiktoken.encoding_for_model(model)
                encoding_model = tiktoken.get_encoding("cl100k_base")
                for message in messages:
                    add_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                    for key, value in message.items():
                        try:
                            add_tokens += len(encoding_model.encode(value))
                        except:
                            try:
                                add_tokens += len(value)
                            except:
                                pass
                        if key == "name":  # if there's a name, the role is omitted
                            add_tokens += -1  # role is always required and always 1 token
                #add_tokens += 1  # every reply is primed with <im_start>assistant

                len_tokens += add_tokens
            except:
                add_tokens = 0
                for message in messages:
                    add_tokens += 4
                    for key, value in message.items():
                        try:
                            add_tokens += len(value)
                        except:
                            pass
                len_tokens += add_tokens

            try:
                add_tokens = 0

                # functionのトークン暫定
                for dic in functions:
                    add_tokens += 19
                    value = dic['description']
                    try:
                        add_tokens += len(encoding_model.encode(value))
                    except:
                        add_tokens += len(value)
                    for x in dic['parameters']['properties']:
                        add_tokens += 5
                        value = dic['parameters']['properties'][x]['description']
                        try:
                            add_tokens += len(encoding_model.encode(value))
                        except:
                            add_tokens += len(value)
                    required = dic['parameters'].get('required')
                    if (required is not None):
                        add_tokens += len(required) + 2

                    len_tokens += add_tokens
            except:
                add_tokens = 0
                for dic in functions:
                    add_tokens += 19
                    value = dic['description']
                    add_tokens += len(value)
                    for x in dic['parameters']['properties']:
                        add_tokens += 5
                        value = dic['parameters']['properties'][x]['description']
                        add_tokens += len(value)
                    required = dic['parameters'].get('required')
                    if (required is not None):
                        add_tokens += len(required) + 2
                len_tokens += add_tokens

            if (select == 'a'):
                if (len_tokens > self.gpt_a_token2):
                    model = self.gpt_a_model3
                    max   = self.gpt_a_token3
                    self.print(session_id, f"tokens { len_tokens } -> { model } ")
                elif (len_tokens > self.gpt_a_token1):
                    model = self.gpt_a_model2
                    max   = self.gpt_a_token2
                    self.print(session_id, f"tokens { len_tokens } -> { model } ")
                if (len_tokens > max):
                    if (model_select == 'auto'):
                        if (self.gpt_b_enable == True):
                            select = 'b'
                            nick_name = self.gpt_b_nick_name
                            model     = self.gpt_b_model1
                            max       = self.gpt_b_token1
            if (select == 'b'):
                if (len_tokens > self.gpt_b_token2):
                    model = self.gpt_b_model3
                    max   = self.gpt_b_token3
                    self.print(session_id, f"tokens { len_tokens } -> { model } ")
                elif (len_tokens > self.gpt_b_token1):
                    model = self.gpt_b_model2
                    max   = self.gpt_b_token2
                    self.print(session_id, f"tokens { len_tokens } -> { model } ")

            if (len_tokens > max):
                nick_name = None
                model     = None
        #except Exception as e:
        #    print(e)

        return nick_name, model, len_tokens



    def files_check(self, filePath=[], ):
        upload_files = []
        image_urls   = []

        # filePath確認
        if (len(filePath) > 0):
            try:

                for file_name in filePath:
                    if (os.path.isfile(file_name)):
                        if (os.path.getsize(file_name) <= 20000000):

                            upload_files.append(file_name)
                            file_ext = os.path.splitext(file_name)[1][1:].lower()
                            if (file_ext in ('jpg', 'jpeg', 'png')):
                                base64_text = base64_encode(file_name)
                                if (file_ext in ('jpg', 'jpeg')):
                                    url = {"url": f"data:image/jpeg;base64,{base64_text}"}
                                    image_url = {'type':'image_url', 'image_url': url}
                                    image_urls.append(image_url)
                                if (file_ext == 'png'):
                                    url = {"url": f"data:image/png;base64,{base64_text}"}
                                    image_url = {'type':'image_url', 'image_url': url}
                                    image_urls.append(image_url)

            except Exception as e:
                print(e)

        return upload_files, image_urls



    def run_gpt(self, chat_class='chat', model_select='auto',
                nick_name=None, model_name=None,
                session_id='admin', history=[], function_modules={},
                sysText=None, reqText=None, inpText='こんにちは',
                upload_files=[], image_urls=[], 
                temperature=0.8, max_step=10, jsonSchema=None, ):

        #self.assistant_id[str(session_id)] = None
        self.thread_id[str(session_id)] = None
        functions = []
        for module_dic in function_modules.values():
            functions.append(module_dic['function'])

        # 戻り値
        res_text    = ''
        res_path    = ''
        res_files   = []
        res_name    = None
        res_api     = None
        res_history = history

        # model 指定
        if (inpText.strip()[:len(self.gpt_a_nick_name)+1].lower() == (self.gpt_a_nick_name.lower() + ',')):
            inpText = inpText.strip()[len(self.gpt_a_nick_name)+1:]
            if   (self.gpt_a_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:len(self.gpt_b_nick_name)+1].lower() == (self.gpt_b_nick_name.lower() + ',')):
            inpText = inpText.strip()[len(self.gpt_b_nick_name)+1:]
            if   (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:len(self.gpt_v_nick_name)+1].lower() == (self.gpt_v_nick_name.lower() + ',')):
            inpText = inpText.strip()[len(self.gpt_v_nick_name)+1:]
            if   (self.gpt_v_enable == True):
                if  (len(image_urls) > 0) \
                and (len(image_urls) == len(upload_files)):
                    model_select = 'v'
            elif (self.gpt_x_enable == True):
                    model_select = 'x'
        elif (inpText.strip()[:len(self.gpt_x_nick_name)+1].lower() == (self.gpt_x_nick_name.lower() + ',')):
            inpText = inpText.strip()[len(self.gpt_x_nick_name)+1:]
            if   (self.gpt_x_enable == True):
                    model_select = 'x'
            elif (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:5].lower() == ('riki,')):
            inpText = inpText.strip()[5:]
            if   (self.gpt_x_enable == True):
                    model_select = 'x'
            elif (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:7].lower() == ('vision,')):
            inpText = inpText.strip()[7:]
            if   (self.gpt_v_enable == True):
                if  (len(image_urls) > 0) \
                and (len(image_urls) == len(upload_files)):
                    model_select = 'v'
            elif (self.gpt_x_enable == True):
                    model_select = 'x'
        elif (inpText.strip()[:10].lower() == ('assistant,')):
            inpText = inpText.strip()[10:]
            if   (self.gpt_x_enable == True):
                    model_select = 'x'
            elif (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:7].lower() == ('openai,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:6].lower() == ('azure,')):
            inpText = inpText.strip()[6:]
            if (self.gpt_a_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:7].lower() == ('claude,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:11].lower() == ('perplexity,')):
            inpText = inpText.strip()[11:]
            if (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:5].lower() == ('pplx,')):
            inpText = inpText.strip()[5:]
            if (self.gpt_b_enable == True):
                    model_select = 'x'
        elif (inpText.strip()[:7].lower() == ('gemini,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'b'
        elif (inpText.strip()[:7].lower() == ('openrt,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:7].lower() == ('ollama,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:6].lower() == ('local,')):
            inpText = inpText.strip()[6:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:7].lower() == ('freeai,')):
            inpText = inpText.strip()[7:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:5].lower() == ('free,')):
            inpText = inpText.strip()[5:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'
        elif (inpText.strip()[:5].lower() == ('groq,')):
            inpText = inpText.strip()[5:]
            if (self.gpt_b_enable == True):
                    model_select = 'a'

        # Vision ?
        if (model_select == 'auto'):
            if (chat_class == 'auto') or (chat_class == 'vision'):
                if  (len(image_urls) > 0) \
                and (len(image_urls) == len(upload_files)):
                    if   (self.gpt_v_enable == True):
                        model_select = 'v'
                    elif (self.gpt_x_enable == True):
                        model_select = 'x'

        # history 追加・圧縮 (古いメッセージ)
        res_history = self.history_add(history=res_history, sysText=sysText, reqText=reqText, inpText=inpText, )
        res_history = self.history_zip1(history=res_history, )

        # メッセージ作成
        if (model_select != 'v'):
            msg = self.history2msg_gpt(history=res_history, )
        else:
            msg = self.history2msg_vision(history=res_history, image_urls=image_urls,)

        # ストリーム実行?
        if (session_id == 'admin') and (self.openai_api_type != 'azure'):
            stream = True
        else:
            stream = False

        # 実行ループ
        #try:
        if True:

            n = 0
            function_name = ''
            while (function_name != 'exit') and (n < int(max_step)):

                # トークン数チェック　→　モデル確定
                res_name, res_api, len_tokens = self.checkTokens(session_id=session_id, messages=msg, functions=functions, model_select=model_select, )
                if (res_api is None):
                    self.print(session_id, f" ChatGPT : Token length over ! ({ len_tokens })")

                    if (len(res_history) > 6):
                        self.print(session_id, ' ChatGPT : History compress !')

                        # history 圧縮 (最後４つ残す)
                        res_history = self.history_zip2(history=res_history, )

                        # メッセージ作成
                        if (model_select != 'v'):
                            msg = self.history2msg_gpt(history=res_history, )
                        else:
                            msg = self.history2msg_vision(history=res_history, image_urls=image_urls,)

                        # トークン数再計算
                        res_name, res_api, len_tokens = self.checkTokens(session_id=session_id, messages=msg, functions=functions, model_select=model_select, )

                if (res_api is None):
                    self.print(session_id, ' ChatGPT : History reset !')

                    # history リセット
                    res_history = []
                    res_history = self.history_add(history=res_history, sysText=sysText, reqText=reqText, inpText=inpText, )
                    #res_history = self.zipHistory(history=res_history, )

                    # メッセージ作成
                    if (model_select != 'v'):
                        msg = self.history2msg_gpt(history=res_history, )
                    else:
                        msg = self.history2msg_vision(history=res_history, image_urls=image_urls,)

                    # トークン数再計算
                    res_name, res_api, len_tokens = self.checkTokens(session_id=session_id, messages=msg, functions=functions, model_select=model_select, )

                if (res_api is None):
                    self.print(session_id, f" ChatGPT : Token length Error ! (functions 無効化！)")

                    # functions 無効化！
                    functions = []

                    # トークン数再計算
                    res_name, res_api, len_tokens = self.checkTokens(session_id=session_id, messages=msg, functions=functions, model_select=model_select, )

                if (res_api is None):
                    self.print(session_id, f" ChatGPT : Token length Error ! ({ len_tokens })")
                    return res_text, res_path, res_files, None, None, res_history

                # o1 モデルは、functions,files 未対応
                if (res_api.lower()[:2] == 'o1'):
                    stream = False
                    functions = []
                    if (len(msg) > 0):
                        if (msg[0]['role'] == 'system'):
                            del msg[0]

                # GPT
                n += 1
                self.print(session_id, f" ChatGPT : { res_name.lower() }, { res_api }, pass={ n }, tokens={ len_tokens }, ")

                # 結果
                res_role      = None
                res_content   = None
                tool_calls    = []

                # https://community.openai.com/t/has-anyone-managed-to-get-a-tool-call-working-when-stream-true/498867/3

                completions = None

                # OPENAI
                if (self.openai_api_type != 'azure'):

                    if   (model_select == 'v') and (len(image_urls) > 0):
                        null_history = self.history_add(history=[], sysText=sysText, reqText=reqText, inpText=inpText, )
                        msg = self.history2msg_vision(history=null_history, image_urls=image_urls,)
                        completions = self.client_v.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                # max_tokens      = 4000,
                                timeout         = self.timeOut, 
                                stream          = stream, 
                                )

                    elif (len(functions) != 0):
                        # ツール設定
                        tools = []
                        for f in range(len(functions)):
                            tools.append({"type": "function", "function": functions[f]})
                        completions = self.client_ab.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                temperature     = float(temperature),
                                tools           = tools,
                                tool_choice     = 'auto',
                                timeout         = self.timeOut,
                                stream          = stream, 
                                )

                    else:
                        if (res_api.lower()[:2] == 'o1'):
                            completions = self.client_ab.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                ###temperature     = float(temperature),
                                timeout         = self.timeOut,
                                stream          = stream, 
                                )

                        elif (jsonSchema is None) or (jsonSchema == ''):
                            completions = self.client_ab.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                temperature     = float(temperature),
                                timeout         = self.timeOut,
                                stream          = stream, 
                                )
                        else:
                            schema = None
                            try:
                                schema = json.loads(jsonSchema)
                            except:
                                pass
                            # スキーマ指定無し
                            if (schema is None):
                                completions = self.client_ab.chat.completions.create(
                                    model           = res_api,
                                    messages        = msg,
                                    temperature     = float(temperature),
                                    timeout         = self.timeOut, 
                                    response_format = { "type": "json_object" },
                                    stream          = stream, 
                                    )
                            # スキーマ指定有り
                            else:
                                completions = self.client_ab.chat.completions.create(
                                    model           = res_api,
                                    messages        = msg,
                                    temperature     = float(temperature),
                                    timeout         = self.timeOut, 
                                    response_format = { "type": "json_schema", "json_schema": schema },
                                    stream          = stream, 
                                    )

                # Azure
                else:

                    if   (model_select == 'v') and (len(image_urls) > 0):
                        null_history = self.history_add(history=[], sysText=sysText, reqText=reqText, inpText=inpText, )
                        msg = self.history2msg_vision(history=null_history, image_urls=image_urls,)
                        completions = self.client_v.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                # max_tokens      = 4000,
                                timeout         = self.timeOut,
                                )

                    elif (len(functions) != 0):
                        # ツール設定
                        tools = []
                        for f in range(len(functions)):
                            tools.append({"type": "function", "function": functions[f]})
                        completions = self.client_ab.chat.completions.create(
                                model           = res_api,
                                messages        = msg,
                                temperature     = float(temperature),
                                tools           = tools,
                                tool_choice     = 'auto',
                                timeout         = self.timeOut,
                                )

                    else:
                        if (res_api.lower()[:2] == 'o1'):
                            completions = self.client_ab.chat.completions.create(
                                    model           = res_api,
                                    messages        = msg,
                                    timeout         = self.timeOut,
                                    )

                        else:
                        # elif (jsonSchema is None) or (jsonSchema == ''):
                            completions = self.client_ab.chat.completions.create(
                                    model           = res_api,
                                    messages        = msg,
                                    temperature     = float(temperature),
                                    timeout         = self.timeOut,
                                    )
                        #else:
                        #    completions = self.client_ab.chat.completions.create(
                        #        model           = res_api,
                        #        messages        = msg,
                        #        temperature     = float(temperature),
                        #        timeout         = self.timeOut, 
                        #        response_format = { "type": "json_object" },
                        #        )

                # Stream 表示
                if (stream == True):
                    chkTime     = time.time()
                    for chunk in completions:
                        if ((time.time() - chkTime) > self.timeOut):
                            break
                        delta   = chunk.choices[0].delta
                        if (delta is not None):
                            if (delta.content is not None):
                                #res_role    = delta.role
                                res_role    = 'assistant'
                                content     = delta.content
                                if (res_content is None):
                                    res_content = ''
                                res_content += content
                                self.stream(session_id, content)

                            elif (delta.tool_calls is not None):
                                #res_role    = delta.role
                                res_role    = 'assistant'
                                tcchunklist = delta.tool_calls
                                for tcchunk in tcchunklist:
                                    if len(tool_calls) <= tcchunk.index:
                                        tool_calls.append({"id": "", "type": "function", "function": { "name": "", "arguments": "" } })
                                    tc = tool_calls[tcchunk.index]
                                    if tcchunk.id:
                                        tc["id"]              += tcchunk.id
                                    if tcchunk.function.name:
                                        tc["function"]["name"] += tcchunk.function.name
                                    if tcchunk.function.arguments:
                                        tc["function"]["arguments"] += tcchunk.function.arguments

                    # 改行
                    if (res_content is not None):
                        self.print(session_id, )
        
                # completions 結果
                if (stream == False):
                    try:
                        res_role    = str(completions.choices[0].message.role)
                        res_content = str(completions.choices[0].message.content)
                    except:
                        pass

                    # 新 function 
                    if (completions.choices[0].finish_reason=='tool_calls'):
                        for tool_call in completions.choices[0].message.tool_calls:
                            t_id     = str(tool_call.id)
                            f_name   = str(tool_call.function.name)
                            f_kwargs = str(tool_call.function.arguments)
                            try:
                                wk_dic      = json.loads(f_kwargs)
                                wk_text     = json.dumps(wk_dic, ensure_ascii=False, )
                                f_kwargs = wk_text
                            except:
                                pass
                            tool_calls.append({"id": t_id, "type": "function", "function": { "name": f_name, "arguments": f_kwargs } })
        
                # function 指示?
                if (len(tool_calls) > 0):

                    # 自動的にbモデルへ切替
                    if (model_select == 'a'):
                        if (self.gpt_b_enable == True):
                            if (self.gpt_b_length != 0):
                                model_select = 'b'

                    self.print(session_id, )
                    for tc in tool_calls:
                        f_name   = tc['function'].get('name')
                        f_kwargs = tc['function'].get('arguments')

                        hit = False

                        for module_dic in function_modules.values():
                            if (f_name == module_dic['func_name']):
                                hit = True
                                self.print(session_id, f" ChatGPT :   function_call '{ module_dic['script'] }' ({ f_name })")
                                self.print(session_id, f" ChatGPT :   → { f_kwargs }")

                                # メッセージ追加格納
                                self.seq += 1
                                dic = {'seq': self.seq, 'time': time.time(), 'role': 'function_call', 'name': f_name, 'content': f_kwargs }
                                res_history.append(dic)

                                # function 実行
                                try:
                                    ext_func_proc  = module_dic['func_proc']
                                    res_json = ext_func_proc( f_kwargs )
                                except Exception as e:
                                    print(e)
                                    # エラーメッセージ
                                    dic = {}
                                    dic['error'] = e 
                                    res_json = json.dumps(dic, ensure_ascii=False, )

                                # tool_result
                                self.print(session_id, f" ChatGPT :   → { res_json }")
                                self.print(session_id, )

                                # メッセージ追加格納
                                dic = {'role': 'function', 'name': f_name, 'content': res_json }
                                msg.append(dic)
                                self.seq += 1
                                dic = {'seq': self.seq, 'time': time.time(), 'role': 'function', 'name': f_name, 'content': res_json }
                                res_history.append(dic)

                                # パス情報確認
                                try:
                                    dic  = json.loads(res_json)
                                    path = dic['image_path']
                                    if (path is None):
                                        path = dic.get('excel_path')
                                    if (path is not None):
                                        res_path = path
                                        res_files.append(path)
                                        res_files = list(set(res_files))
                                except:
                                    pass

                                break

                        if (hit == False):
                            self.print(session_id, f" ChatGPT :   function_call Error ! ({ f_name })")
                            print(res_role, res_content, f_name, f_kwargs, )
                            break

                # GPT 会話終了
                elif (res_role == 'assistant') and (res_content is not None):
                    function_name   = 'exit'
                    self.print(session_id, f" ChatGPT : { res_name.lower() }, complete.")

                    # 自動で(B)モデル(GPT4)実行
                    if (model_select == 'auto') or (model_select == 'a'):
                        if (self.gpt_b_enable == True):
                            if (res_name != self.gpt_b_nick_name):
                                if (self.gpt_b_length != 0) and (len(res_text) >= self.gpt_b_length):
                                    res_name2, res_api2, len_tokens = self.checkTokens(session_id=session_id, messages=msg, functions=[], model_select='b', )
                                    if (res_api2 is not None):
                                        self.print(session_id, f" ChatGPT : { res_name2.lower() } start.")

                                        try:
                                            # OPENAI
                                            if (self.openai_api_type != 'azure'):
                                                completions2 = self.client_ab.chat.completions.create(
                                                    model       = res_api2,
                                                    messages    = msg,
                                                    temperature = float(temperature),
                                                    timeout     = self.timeOut, )

                                            # Azure
                                            else:
                                                completions2 = self.client_ab.chat.completions.create(
                                                    model       = res_api2,
                                                    messages    = msg,
                                                    temperature = float(temperature),
                                                    timeout     = self.timeOut, )

                                            res_role2    = str(completions2.choices[0].message.role)
                                            res_content2 = str(completions2.choices[0].message.content)
                                            if (res_role2 == 'assistant') and (res_content2 is not None):
                                                res_name    = res_name2
                                                res_api     = res_api2
                                                res_role    = res_role2
                                                res_content = res_content2
                                                self.print(session_id, f" ChatGPT : { res_name.lower() }, complete.")
                                        except Exception as e:
                                            print(e)
                                            self.print(session_id, f" ChatGPT : { res_name2.lower() } error!")

            # 正常回答
            if (res_content is not None):
                #self.print(session_id, res_content.rstrip())
                res_text += res_content.rstrip()

            # 異常回答
            else:
                self.print(session_id, ' ChatGPT : Error !')

            # History 追加格納
            if (res_text.strip() != ''):
                self.seq += 1
                dic = {'seq': self.seq, 'time': time.time(), 'role': res_role, 'name': '', 'content': res_text }
                res_history.append(dic)

        #except Exception as e:
        #    print(e)
        #    res_text = ''

        return res_text, res_path, res_files, res_name, res_api, res_history



    def vectorStore_del(self, session_id='admin', assistant_id=None, assistant_name='', ):

        # 2024/04/21時点 azure 未対応
        if (self.openai_api_type == 'azure'):
            return False

        # vector store 削除
        vector_stores = self.client_x.vector_stores.list()
        for v in range(len(vector_stores.data)):
            vs_id   = vector_stores.data[v].id
            vs_name = vector_stores.data[v].name
            if (vs_name == assistant_name):

                vs_files = self.client_x.vector_stores.files.list(vector_store_id=vs_id)

                for f in range(len(vs_files.data)):
                    file_id   = vs_files.data[f].id
                    self.client_x.files.delete(file_id=file_id, )
                self.print(session_id, f"  vector store delete! ('{ vs_name }')")
                self.client_x.vector_stores.delete(vector_store_id=vs_id)

                break
        
        return True

    def vectorStore_set(self, session_id='admin', retrievalFiles_path='_extensions/retrieval_files/', assistant_id=None, assistant_name='', ):
        vectorStore_ids = []

        # 2024/04/21時点 azure 未対応
        if (self.openai_api_type == 'azure'):
            return vectorStore_ids

        # ファイル一覧
        proc_files = []
        path_files = glob.glob(retrievalFiles_path + '*.*')
        path_files.sort()
        if (len(path_files) > 0):
            for f in path_files:
                proc_files.append(os.path.basename(f))

        # マッチング検査 違いがあれば vector store 削除
        vector_stores = self.client_x.vector_stores.list()
        for v in range(len(vector_stores.data)):
            vs_id   = vector_stores.data[v].id
            vs_name = vector_stores.data[v].name
            if (vs_name == assistant_name):
                vs_files = self.client_x.vector_stores.files.list(vector_store_id=vs_id)

                vectorStore_ids = [vs_id]
                if (len(proc_files) != len(vs_files.data)):
                    vectorStore_ids = []
                else:
                    for f in range(len(vs_files.data)):
                        file_id   = vs_files.data[f].id
                        file_info = self.client_x.files.retrieve(file_id=file_id, )
                        file_name = file_info.filename
                        if (file_name not in proc_files):
                            vectorStore_ids = []
                            break

                if (len(vectorStore_ids) == 0):
                    for f in range(len(vs_files.data)):
                        file_id   = vs_files.data[f].id
                        self.client_x.files.delete(file_id=file_id, )
                    self.print(session_id, f" Assistant : Delete vector store = '{ vs_name }', ")
                    self.client_x.vector_stores.delete(vector_store_id=vs_id)

                break

        # 転送不要
        if (len(vectorStore_ids) == len(proc_files)):
            return vectorStore_ids

        # vector store 作成
        if (len(proc_files) > 0):

            # ファイル
            upload_ids   = []
            for proc_file in proc_files:
                file_name = retrievalFiles_path + proc_file
                if (os.path.isfile(file_name)):

                    # アップロード済み確認
                    file_id = None
                    assistant_files_list = self.client_x.files.list()
                    for n in range(len(assistant_files_list.data)):
                        if (proc_file == assistant_files_list.data[n].filename):
                            file_id   = assistant_files_list.data[n].id
                            print(f" Assistant : Hit file_name = '{ proc_file }', { file_id }")
                            break

                    # アップロード
                    if (file_id == None):
                        try:
                            # アップロード
                            file = open(file_name, 'rb')
                            upload = self.client_x.files.create(
                                        file    = file,
                                        purpose = 'assistants', )
                            file_id = upload.id
                            print(f" Assistant : Upload file_name = '{ proc_file }', { file_id }")
                        except Exception as e:
                            print(e)

                    if (file_id != None):
                        upload_ids.append(file_id)

            # ベクターストア作成
            if (len(upload_ids) > 0):
                try:

                    vector_store = self.client_x.vector_stores.create(
                                        name = assistant_name,
                                        #expires_after = {
                                        #"anchor": "last_active_at",
                                        #"days": 2
                                        #}
                                    )

                    file_batch = self.client_x.vector_stores.file_batches.create_and_poll(
                                        vector_store_id = vector_store.id,
                                        file_ids        = upload_ids,
                                    )

                    self.print(session_id, f" Assistant : { file_batch.status }")

                    vectorStore_ids = [vector_store.id]

                except Exception as e:
                    print(e)

        # デバッグ用 アップロード確認
        if False:
            vector_stores = self.client_x.vector_stores.list()
            for v in range(len(vector_stores.data)):
                vs_id   = vector_stores.data[v].id
                vs_name = vector_stores.data[v].name
                if (vs_name == assistant_name):
                    self.print(session_id, vs_name)
                    vs_files = self.client_x.vector_stores.files.list(vector_store_id=vs_id)
                    for f in range(len(vs_files.data)):
                        file_id   = vs_files.data[f].id
                        file_info = self.client_x.files.retrieve(
                            file_id=file_id, )
                        file_name = file_info.filename
                        self.print(session_id, file_name)

        return vectorStore_ids

    def threadFile_del(self, session_id='admin', assistant_id=None, assistant_name='', ):

        # 2024/04/21時点 azure 未対応
        if (self.openai_api_type == 'azure'):
            return False

        assistant_files_list = self.client_x.files.list()
        for f in range(len(assistant_files_list.data)):
            file_id   = assistant_files_list.data[f].id
            file_name = assistant_files_list.data[f].filename

            x = len(assistant_name)
            if (file_name[:x] == assistant_name):
                res = self.client_x.files.delete(
                    file_id=file_id, )

        return True

    def threadFile_set(self, session_id='admin', upload_files=[], assistant_id=None, assistant_name='', ):
        upload_ids = []

        # 2024/04/21時点 azure 未対応
        if (self.openai_api_type == 'azure'):
            return upload_ids

        for upload_file in upload_files:
            base_name   = os.path.basename(upload_file)
            work_name   = assistant_name + '_' + base_name
            upload_work = qPath_chat_work + work_name
            shutil.copy(upload_file, upload_work)

            # 既に存在なら、置換えの為、削除
            assistant_files_list = self.client_x.files.list()
            for f in range(len(assistant_files_list.data)):
                file_id   = assistant_files_list.data[f].id
                file_name = assistant_files_list.data[f].filename
                if (file_name == work_name):
                    res = self.client_x.files.delete(
                        file_id=file_id, )

            # アップロード
            upload = self.client_x.files.create(
                file = open(upload_work, 'rb'),
                purpose='assistants', )
            upload_ids.append(upload.id)

            self.print(session_id, f" Assistant : Upload ... { upload.id }, { base_name },")

            # proc? wait
            #time.sleep(0.50)

        return upload_ids

    def threadFile_reset(self, session_id='admin', upload_ids=[], assistant_id=None, assistant_name='', ):

        # 2024/04/21時点 azure 未対応
        if (self.openai_api_type == 'azure'):
            return False

        # 削除
        for upload_id in upload_ids:
            try:
                res = self.client_x.files.delete(
                    file_id=upload_id, )
                self.print(session_id, f" Assistant : Delete ... { upload_id },")
            except:
                pass

        return True

    def my_assistant_update(self, session_id='admin', my_assistant_id=None, my_assistant_name='',
                            model_name='gpt-4o', instructions='', 
                            function_list=[], vectorStore_ids=[], upload_ids=[], ):

        try:

            # ツール設定
            tools = []
            if (model_name[:1].lower() != 'o'): # o1, o3, ... 以外
                tools.append({"type": "code_interpreter"})
                if (len(vectorStore_ids) > 0):
                    tools.append({"type": "file_search"})
            if (len(function_list) != 0):
                for f in range(len(function_list)):
                    tools.append({"type": "function", "function": function_list[f]})
            #print(tools)

            # アシスタント取得
            assistant = self.client_x.beta.assistants.retrieve(
                assistant_id = my_assistant_id, )
            try:
                as_vector_ids = []
                as_vector_ids = assistant.tool_resources.file_search.vector_store_ids
            except:
                pass
            try:
                as_file_ids   = []
                as_file_ids   = assistant.tool_resources.code_interpreter.file_ids
            except:
                pass

            # アシスタント更新
            change_flag = False
            if (model_name      != assistant.model):
                change_flag = True
                self.print(session_id, f" Assistant : Change model, { model_name },")
            if (instructions    != assistant.instructions):
                change_flag = True
                self.print(session_id, f" Assistant : Change instructions ...")
            if (len(tools)      != len(assistant.tools)):
                change_flag = True
                self.print(session_id, f" Assistant : Change tools ...")
                #self.print(tools, )
                #self.print(assistant.tools, )
            if (vectorStore_ids != as_vector_ids):
                change_flag = True
                self.print(session_id, f" Assistant : Change vector store ids ...")
            if (upload_ids      != as_file_ids):
                change_flag = True
                self.print(session_id, f" Assistant : Change file ids ...")

            if (change_flag != True):
                return False
            else:
                self.print(session_id, f" Assistant : Update assistant_name = '{ my_assistant_name }',")

                # OPENAI
                if (self.openai_api_type != 'azure'):

                    tool_resources = {}
                    if (model_name[:1].lower() != 'o'): # o1, o3, ... 以外
                        if (len(vectorStore_ids) > 0):
                            tool_resources["file_search"] = { "vector_store_ids": vectorStore_ids }
                        if (len(upload_ids) > 0):
                            tool_resources["code_interpreter"] = { "file_ids": upload_ids }

                    assistant = self.client_x.beta.assistants.update(
                                        assistant_id = my_assistant_id,
                                        model        = model_name,
                                        instructions = instructions,
                                        tools        = tools,
                                        timeout      = int(self.timeOut * 3),
                                        tool_resources = tool_resources,
                                    )

                # Azure
                else:

                    assistant = self.client_x.beta.assistants.update(
                                        assistant_id = my_assistant_id,
                                        model        = model_name,
                                        instructions = instructions,
                                        tools        = tools,
                                        timeout      = int(self.timeOut * 3),

                                        # 2024/04/21時点 azure 未対応
                                        #tool_resources = {
                                        #    "file_search": {
                                        #        "vector_store_ids": vectorStore_ids
                                        #        },
                                        #    "code_interpreter": {
                                        #        "file_ids": upload_ids
                                        #        }
                                        #    },
                                    )

        except Exception as e:
            print(e)
            return False
        return True

    def run_assistant(self, chat_class='assistant', model_select='auto',
                      nick_name=None, model_name=None,
                      session_id='admin', history=[], function_modules={},
                      sysText=None, reqText=None, inpText='こんにちは',
                      upload_files=[], image_urls=[],
                      temperature=0.8, max_step=10, jsonSchema=None, ):

        function_list = []
        for module_dic in function_modules.values():
            function_list.append(module_dic['function'])

        # 戻り値
        res_text    = ''
        res_path    = ''
        res_files   = []
        if (nick_name  is None):
            nick_name   = self.gpt_x_nick_name
        if (model_name is None):
            model_name  = self.gpt_x_model1
        res_history = history

        # モデル設定（1 -> 2）
        if (chat_class == 'knowledge') \
        or (chat_class == 'code_interpreter'):
            if (self.gpt_x_model2 != ''):
                model_name  = self.gpt_x_model2

        # model 指定文字削除
        if (self.gpt_a_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_a_nick_name)+1].lower() == (self.gpt_a_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_a_nick_name)+1:]
        if (self.gpt_b_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_b_nick_name)+1].lower() == (self.gpt_b_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_b_nick_name)+1:]
        if (self.gpt_v_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_v_nick_name)+1].lower() == (self.gpt_v_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_v_nick_name)+1:]
                if (self.gpt_v_enable == True):
                    if  (len(image_urls) > 0) \
                    and (len(image_urls) == len(upload_files)):
                        nick_name  = self.gpt_v_nick_name
                        model_name = self.gpt_v_model
        if (self.gpt_x_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_x_nick_name)+1].lower() == (self.gpt_x_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_x_nick_name)+1:]
        if   (inpText.strip()[:5].lower() == ('riki,')):
            inpText = inpText.strip()[5:]
        elif (inpText.strip()[:7].lower() == ('vision,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:10].lower() == ('assistant,')):
            inpText = inpText.strip()[10:]
        elif (inpText.strip()[:7].lower() == ('openai,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:6].lower() == ('azure,')):
            inpText = inpText.strip()[6:]
        elif (inpText.strip()[:7].lower() == ('claude,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:11].lower() == ('perplexity,')):
            inpText = inpText.strip()[11:]
        elif (inpText.strip()[:5].lower() == ('pplx,')):
            inpText = inpText.strip()[5:]
        elif (inpText.strip()[:7].lower() == ('gemini,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:7].lower() == ('openrt,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:7].lower() == ('ollama,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:6].lower() == ('local,')):
            inpText = inpText.strip()[6:]
        elif (inpText.strip()[:7].lower() == ('freeai,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:5].lower() == ('free,')):
            inpText = inpText.strip()[5:]
        elif (inpText.strip()[:5].lower() == ('groq,')):
            inpText = inpText.strip()[5:]

        # history 追加・圧縮 (古いメッセージ)
        res_history = self.history_add(history=res_history, sysText=sysText, reqText=reqText, inpText=inpText, )
        res_history = self.history_zip1(history=res_history, )

        # 結果
        res_role      = None
        res_content   = None

        upload_ids    = []

        exit_status   = None
        last_status   = None

        # アシスタント確認
        my_assistant_name   = self.assistant_name + '-' + str(session_id)
        my_assistant_id     = self.assistant_id.get(str(session_id))
        if (my_assistant_id is None):

            # 動作設定
            instructions = sysText
            if (instructions is None) or (instructions == ''):
                instructions = 'あなたは優秀なアシスタントです。'

            # アシスタント検索
            assistants = self.client_x.beta.assistants.list(
                order = "desc",
                limit = "100", )
            for a in range(len(assistants.data)):
                assistant = assistants.data[a]
                if (assistant.name == my_assistant_name):
                    my_assistant_id = assistant.id
                    break

            # アシスタント生成
            if (my_assistant_id is None):

                # アシスタント削除
                if (self.max_session > 0) and (len(assistants.data) > 0):
                    for a in range(self.max_session -1 , len(assistants.data)):
                        assistant = assistants.data[a]
                        if (assistant.name != my_assistant_name):
                            self.print(session_id, f" Assistant : Delete assistant_name = '{ assistant.name }',")

                            # vector store 削除
                            res = self.vectorStore_del(session_id     = session_id,
                                                       assistant_id   = my_assistant_id, 
                                                       assistant_name = my_assistant_name, )
  
                            # ファイル 削除
                            res = self.threadFile_del(session_id     = session_id,
                                                      assistant_id   = my_assistant_id,
                                                      assistant_name = my_assistant_name, )

                            # アシスタント削除
                            res = self.client_x.beta.assistants.delete(assistant_id = assistant.id, )

                # アシスタント生成
                self.print(session_id, f" Assistant : Create assistant_name = '{ my_assistant_name }',")
                assistant = self.client_x.beta.assistants.create(
                    name     = my_assistant_name,
                    model    = model_name,
                    instructions = instructions,
                    tools    = [], )
                my_assistant_id = assistant.id
                self.assistant_id[str(session_id)] = my_assistant_id

            # vector store 作成
            vectorStore_ids = self.vectorStore_set(session_id          = session_id,
                                                   retrievalFiles_path = '_extensions/retrieval_files/',
                                                   assistant_id        = my_assistant_id, 
                                                   assistant_name      = my_assistant_name, )

            # ファイルアップロード
            upload_ids = self.threadFile_set(session_id     = session_id,
                                             upload_files   = upload_files,
                                             assistant_id   = my_assistant_id,
                                             assistant_name = my_assistant_name, )
            #self.print(session_id, f"##{ upload_ids }##")
            # proc? wait
            #if (len(upload_files) > 0):
            #    time.sleep(1.00 * len(upload_files))

            # アシスタント更新
            if (my_assistant_id is not None):
                res = self.my_assistant_update( session_id        = session_id,
                                                my_assistant_id   = my_assistant_id,
                                                my_assistant_name = my_assistant_name,
                                                model_name        = model_name, 
                                                instructions      = instructions, 
                                                function_list     = function_list,
                                                vectorStore_ids   = vectorStore_ids,
                                                upload_ids        = upload_ids, )
                # proc? wait
                #if (res == True):
                #    time.sleep(1.00)

        # スレッド確認
        my_thread_id = self.thread_id.get(str(session_id))
        if (my_thread_id is None):

            # スレッド生成
            self.print(session_id, f" Assistant : Create thread (assistant_name) = '{ my_assistant_name }',")
            thread = self.client_x.beta.threads.create(
                metadata = {'assistant_name': my_assistant_name}, )
            my_thread_id = thread.id
            self.thread_id[str(session_id)] = my_thread_id

            # 過去メッセージ追加
            for m in range(len(res_history) - 1):
                role    = res_history[m].get('role','')
                content = res_history[m].get('content','')
                name    = res_history[m].get('name','')
                if (role != 'system'):
                    # 全てユーザーメッセージにて処理
                    if (name is None) or (name == ''):
                        msg_text = '(' + role + ')' + '\n' + content
                    else:
                        if (role == 'function_call'):
                            msg_text = '(function ' + name + ' call)'  + '\n' + content
                        else:
                            msg_text = '(function ' + name + ' result) ' + '\n' + content
                    #self.print(session_id, msg_text)
                    res = self.client_x.beta.threads.messages.create(
                        thread_id = my_thread_id,
                        role      = 'user',
                        content   = msg_text, )

        # メッセージ生成
        content_text = ''
        if (reqText is not None) and (reqText.strip() != ''):
            content_text += reqText.rstrip() + '\n'
        if (inpText is not None) and (inpText.strip() != ''):
            content_text += inpText.rstrip() + '\n'
        res = self.client_x.beta.threads.messages.create(
            thread_id = my_thread_id,
            role      = 'user',
            content   = content_text, )

        # ストリーム実行?
        if (session_id == 'admin'):
            stream = True
        else:
            stream = False

        # 実行開始        
        #try:
        if True:
            if (stream == True):
                # 初期化
                my_handler = my_eventHandler(log_queue=self.log_queue, my_seq=self.seq,
                                            auto_continue=self.auto_continue, max_step=max_step,
                                            my_client=self.client_x, 
                                            my_assistant_id=my_assistant_id, my_assistant_name=my_assistant_name,
                                            my_thread_id=my_thread_id,
                                            session_id=session_id, res_history=res_history, function_modules=function_modules,
                                            res_text=res_text, res_path=res_path, res_files=res_files, 
                                            upload_files=upload_files, upload_flag=False, )

                # 実行
                try:
                    with self.client_x.beta.threads.runs.stream(
                        assistant_id = my_assistant_id,
                        thread_id    = my_thread_id,
                        event_handler=my_handler,
                    ) as stream:
                        stream.until_done()
                except Exception as e:
                    print(e)

                self.seq     = my_handler.my_seq
                res_history  = my_handler.res_history
                res_text     = my_handler.res_text
                res_path     = my_handler.res_path
                res_files    = my_handler.res_files
                upload_files = my_handler.upload_files
                upload_flag  = my_handler.upload_flag

                res_role     = 'assistant'

                if (upload_flag == True):

                    # アシスタント更新
                    res = self.my_assistant_update( session_id        = session_id,
                                                    my_assistant_id   = my_assistant_id,
                                                    my_assistant_name = my_assistant_name,
                                                    model_name        = model_name, 
                                                    instructions      = instructions, 
                                                    function_list     = function_list,
                                                    vectorStore_ids   = vectorStore_ids,
                                                    upload_ids        = upload_ids, )

                # 終了待機
                exit_status = my_handler.my_run_status

            else:
                # 実行開始
                run = self.client_x.beta.threads.runs.create(
                    assistant_id = my_assistant_id,
                    thread_id    = my_thread_id, )
                my_run_id = run.id

                # 実行ループ
                exit_status    = None
                last_status    = None
                count_run_step = 0
                messages = self.client_x.beta.threads.messages.list(
                        thread_id = my_thread_id, 
                        order     = 'asc', )
                last_msg_step = len(messages.data) # First msg is request
                last_message  = None
                
                chkTime       = time.time()
                while (exit_status is None) and ((time.time() - chkTime) < (self.timeOut * 5)):

                    # ステータス
                    run = self.client_x.beta.threads.runs.retrieve(
                        thread_id = my_thread_id,
                        run_id    = my_run_id, )
                    if (run.status != last_status):
                        last_status = run.status
                        chkTime     = time.time()
                        self.print(session_id, f" Assistant : { last_status }")

                    # 完了時は少し待機
                    #if (last_status == 'completed'):
                    #    time.sleep(0.25)

                    # 実行ステップ確認
                    #time.sleep(0.25)
                    run_steps = self.client_x.beta.threads.runs.steps.list(
                            thread_id = my_thread_id,
                            run_id    = my_run_id,
                            order     = 'asc', )
                    if (len(run_steps.data) > count_run_step):
                        for r in range(count_run_step, len(run_steps.data)):
                            step_details_type = run_steps.data[r].step_details.type
                            if (step_details_type != 'tool_calls'):
                                self.print(session_id, f" Assistant : ({ step_details_type })")
                            else:
                                #self.print(session_id, run_steps.data[r].step_details)
                                step_details_tool_type = None
                                try:
                                    step_details_tool_type = run_steps.data[r].step_details.tool_calls[0].type
                                except:
                                    try:
                                        tc = run_steps.data[r].step_details.tool_calls[0]
                                        step_details_tool_type = tc.get('type')
                                    except:
                                        pass
                                if (step_details_tool_type is not None):
                                    self.print(session_id, f" Assistant : ({ step_details_tool_type }...)")
                                else:
                                    self.print(session_id, f" Assistant : ({ step_details_type })")

                            if (step_details_type == 'message_creation'):
                                message_id = run_steps.data[r].step_details.message_creation.message_id
                                if (message_id is not None):
                                    messages = self.client_x.beta.threads.messages.retrieve(
                                            thread_id  = my_thread_id, 
                                            message_id = message_id, )
                                    for c in range(len(messages.content)):
                                        content_type = messages.content[c].type
                                        if (content_type == 'text'):
                                            content_value = messages.content[c].text.value
                                            if (content_value is not None) and (content_value != ''):
                                                if (last_status != 'completed'):
                                                    if (content_value != last_message):
                                                        last_message = content_value 
                                                        self.print(session_id, last_message)
                                                        self.print(session_id, )

                        count_run_step = len(run_steps.data)

                    # 最大ステップ  10step x (3auto+1) / 2 = 20
                    limit_step = int((int(max_step) * (int(self.auto_continue)+1)) / 2)
                    if (count_run_step > limit_step):
                        exit_status = 'overstep'
                        self.print(session_id, f" Assistant : overstep! (n={ count_run_step }!)")
                        break

                    # 実行メッセージ確認
                    #time.sleep(0.25)
                    messages = self.client_x.beta.threads.messages.list(
                            thread_id = my_thread_id, 
                            order     = 'asc', )
                    if (len(messages.data) > last_msg_step):
                        for m in range(last_msg_step, len(messages.data)):

                            res_role = messages.data[m].role
                            for c in range(len(messages.data[m].content)):
                                content_type = messages.data[m].content[c].type
                                #if (content_type == 'image_file'):
                                #    file_type   = content_type
                                #    file_id     = messages.data[m].content[c].image_file.file_id
                                #    if (file_id is not None):
                                #        self.print(session_id, f" Assistant : ( { file_type }, { file_id } )")

                                if (content_type == 'text'):
                                    content_value = messages.data[m].content[c].text.value
                                    if (content_value is not None) and (content_value != ''):
                                        last_msg_step = m
                                        if (last_status != 'completed'):
                                            if (content_value != last_message):
                                                last_message = content_value 
                                                self.print(session_id, last_message)
                                                self.print(session_id, )
                                        else:
                                            res_content  = content_value

                                    for a in range(len(messages.data[m].content[c].text.annotations)):
                                        try:
                                            file_type = messages.data[m].content[c].text.annotations[a].type
                                            file_text = messages.data[m].content[c].text.annotations[a].text
                                            file_id   = messages.data[m].content[c].text.annotations[a].file_path.file_id

                                            file_dic  = self.client_x.files.retrieve(file_id)
                                            filename = os.path.basename(file_dic.filename)
                                            content_file = self.client_x.files.content(file_id)
                                            data_bytes   = content_file.read()
                                            with open(qPath_output + filename, "wb") as file:
                                                file.write(data_bytes)

                                            res_path = qPath_output + filename
                                            self.print(session_id, f" Assistant : Download ... { file_text }")
                                        except:
                                            pass

                    # 処理中
                    if   (last_status == 'in_progress') \
                    or   (last_status == 'queued') \
                    or   (last_status == 'cancelling'):
                        pass

                    # 終了
                    elif (last_status == 'completed') \
                    or   (last_status == 'cancelled') \
                    or   (last_status == 'failed') \
                    or   (last_status == 'expired'):
                        exit_status = last_status

                        # 正常終了
                        if (last_status == 'completed'):
                            break

                        # その他終了
                        else:
                            self.print(session_id, ' Assistant : !')
                            break

                    # ファンクション
                    elif (last_status == 'requires_action'):
                        tool_result = []
                        upload_flag = False

                        self.print(session_id, )
                        tool_calls = run.required_action.submit_tool_outputs.tool_calls
                        for t in range(len(tool_calls)):
                            tool_call_id  = tool_calls[t].id
                            function_name = tool_calls[t].function.name
                            json_kwargs   = tool_calls[t].function.arguments

                            hit = False
                            for module_dic in function_modules.values():
                                if (function_name == module_dic['func_name']):
                                    hit = True
                                    self.print(session_id, f" Assistant :   function_call '{ module_dic['script'] }' ({  function_name })")
                                    self.print(session_id, f" Assistant :   → { json_kwargs }")

                                    chkTime     = time.time()

                                    # メッセージ追加格納
                                    self.seq += 1
                                    dic = {'seq': self.seq, 'time': time.time(), 'role': 'function_call', 'name': function_name, 'content': json_kwargs }
                                    res_history.append(dic)

                                    # function 実行
                                    try:
                                        ext_func_proc  = module_dic['func_proc']
                                        res_json       = ext_func_proc( json_kwargs )
                                    except Exception as e:
                                        print(e)
                                        # エラーメッセージ
                                        dic = {}
                                        dic['error'] = e 
                                        res_json = json.dumps(dic, ensure_ascii=False, )

                                    chkTime     = time.time()

                                    # メッセージ追加格納
                                    self.seq += 1
                                    dic = {'seq': self.seq, 'time': time.time(), 'role': 'function', 'name': function_name, 'content': res_json }
                                    res_history.append(dic)

                                    # パス情報確認
                                    try:
                                        dic  = json.loads(res_json)
                                        path = dic.get('image_path')
                                        if (path is None):
                                            path = dic.get('excel_path')
                                        if (path is not None):
                                            res_path = path
                                            res_files.append(path)
                                            upload_files.append(path)
                                            res_files    = list(set(res_files))
                                            upload_files = list(set(upload_files))

                                            # ファイルアップロード
                                            upload_ids = self.threadFile_set(session_id     = session_id,
                                                                            upload_files   = upload_files,
                                                                            assistant_id   = my_assistant_id,
                                                                            assistant_name = my_assistant_name, )
                                            upload_flag = True

                                    except Exception as e:
                                        print(e)

                            if (hit == False):
                                self.print(session_id, f" Assistant :   function_call Error ! ({ function_name })")
                                self.print(session_id, json_kwargs, )

                                dic = {}
                                dic['result'] = 'error' 
                                res_json = json.dumps(dic, ensure_ascii=False, )

                            # tool_result
                            self.print(session_id, f" Assistant :   → { res_json }")
                            self.print(session_id, )
                            tool_result.append({"tool_call_id": tool_call_id, "output": res_json})

                        # 結果通知
                        run = self.client_x.beta.threads.runs.submit_tool_outputs(
                            thread_id    = my_thread_id,
                            run_id       = my_run_id,
                            tool_outputs = tool_result, )

                        # アシスタント更新
                        if (upload_flag == True):
                            res = self.my_assistant_update(session_id        = session_id,
                                                        my_assistant_id   = my_assistant_id,
                                                        my_assistant_name = my_assistant_name,
                                                        model_name        = model_name, 
                                                        instructions      = instructions, 
                                                        functions         = functions,
                                                        vectorStore_ids   = vectorStore_ids,
                                                        upload_ids        = upload_ids, )

                    else:
                        self.print(session_id, run)
                        self.print(session_id, )
                        #time.sleep(0.50)

        #except Exception as e:
        #    print(e)
        #    res_content = None

        if (exit_status is None):
            exit_status = 'timeout'
            self.print(session_id, f" Assistant : timeout! ({ str(self.timeOut * 5) }s)")
            #raise RuntimeError('assistant run timeout !')
            
        # 結果確認
        if (exit_status == 'completed'):

            if (res_content is not None):
                #self.print(session_id, res_content.rstrip())
                res_text += res_content.rstrip() + '\n'

            # History 追加格納
            self.seq += 1
            dic = {'seq': self.seq, 'time': time.time(), 'role': res_role, 'name': '', 'content': res_text }
            res_history.append(dic)

        # 異常終了
        else:
            res_text = ''

            # History 追加格納
            self.seq += 1
            dic = {'seq': self.seq, 'time': time.time(), 'role': 'assistant', 'name': '', 'content': exit_status }
            res_history.append(dic)

        # 実行キャンセル
        runs = self.client_x.beta.threads.runs.list(
            thread_id = my_thread_id, )
        for r in range(len(runs.data)):
            run_id     = runs.data[r].id
            run_status = runs.data[r].status
            if  (run_status != 'completed') \
            and (run_status != 'cancelled') \
            and (run_status != 'failed') \
            and (run_status != 'expired') \
            and (run_status != 'cancelling'):
                try:
                    run = self.client_x.beta.threads.runs.cancel(
                        thread_id = my_thread_id, 
                        run_id    = run_id, )
                    self.print(session_id, f" Assistant : run cancel ... { run_id }")
                except:
                    pass

        # ファイル削除
        #res = self.threadFile_reset(session_id     = session_id,
        #                            upload_ids     = upload_ids,
        #                            assistant_id   = my_assistant_id,
        #                            assistant_name = my_assistant_name, )
        self.work_upload_ids     = upload_ids
        self.work_assistant_id   = my_assistant_id
        self.work_assistant_name = my_assistant_name

        return res_text, res_path, res_files, nick_name, model_name, res_history

    def auto_assistant(self, chat_class='chat', model_select='auto',
                      nick_name=None, model_name=None,
                      session_id='admin', history=[], function_modules={}, 
                      sysText=None, reqText=None, inpText='こんにちは',
                      upload_files=[], image_urls=[],
                      temperature=0.8, max_step=10, jsonSchema=None, ):

        # 戻り値
        res_text    = ''
        res_path    = ''
        res_files   = []
        if (nick_name  is None):
            nick_name   = self.gpt_x_nick_name
        if (model_name is None):
            model_name  = self.gpt_x_model1
        res_history = history

        # ファイル削除
        #res = self.threadFile_reset(session_id     = session_id,
        #                            upload_ids     = work_upload_ids,
        #                            assistant_id   = work_assistant_id,
        #                            assistant_name = work_assistant_name, )
        self.work_upload_ids     = None
        self.work_assistant_id   = None
        self.work_assistant_name = None

        # モデル設定（1 -> 2）
        if (chat_class == 'knowledge') \
        or (chat_class == 'code_interpreter'):
            if (self.gpt_x_model2 != ''):
                model_name  = self.gpt_x_model2

        # model 指定文字削除
        if (self.gpt_a_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_a_nick_name)+1].lower() == (self.gpt_a_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_a_nick_name)+1:]
        if (self.gpt_b_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_b_nick_name)+1].lower() == (self.gpt_b_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_b_nick_name)+1:]
        if (self.gpt_v_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_v_nick_name)+1].lower() == (self.gpt_v_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_v_nick_name)+1:]
        if (self.gpt_x_nick_name != ''):
            if (inpText.strip()[:len(self.gpt_x_nick_name)+1].lower() == (self.gpt_x_nick_name.lower() + ',')):
                inpText = inpText.strip()[len(self.gpt_x_nick_name)+1:]
        if   (inpText.strip()[:5].lower() == ('riki,')):
            inpText = inpText.strip()[5:]
        elif (inpText.strip()[:7].lower() == ('vision,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:10].lower() == ('assistant,')):
            inpText = inpText.strip()[10:]
        elif (inpText.strip()[:7].lower() == ('openai,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:6].lower() == ('azure,')):
            inpText = inpText.strip()[6:]
        elif (inpText.strip()[:7].lower() == ('claude,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:7].lower() == ('gemini,')):
            inpText = inpText.strip()[7:]
        elif (inpText.strip()[:6].lower() == ('local,')):
            inpText = inpText.strip()[6:]

        # history 圧縮 (最後４つ残す)
        old_history = self.history_zip2(history=history, )

# ----- あなたの役割 -----
# あなたは、会話履歴と最後のユーザーの要求、ＡＩ応答から、継続実行の必要性、回答評価を行います。
# 回答は以下のjsonスキーマ形式でお願いします。
# '{"continue": str, "result_point": str, "assessment_text": str,}'
#
# ----- あなたへの依頼 -----
# 継続実行の必要性はcontinueとして、no,yes,stopで回答してください。(例) yes
# 回答評価はresult_pointで、ユーザー要求に対して、達成率で回答してください。(例) 30
# 回答評価した理由assessment_textもお願いします。(例) 動くソース要求に対して回答がメインロジックのみの回答
# 以下の条件で、回答してください。
# 1) ユーザーの要求に到達している場合、continue=no,result_point=達成率,assessment_text=評価理由
# 2) 処理途中と思われる場合で、ユーザーが新たな要求入力として「適切に判断して処理を継続してください」と入力した場合に適切に処理を継続出来そうな場合、continue=yes,result_point=達成率,assessment_text=評価理由
# 3) 上記以外の場合や継続実行がむつかしいと考えられる場合、continue=stop,result_point=達成率,assessment_text=評価理由

        # GPT 評価判定（準備）
        auto_jsonSchema = '{"continue": str, "result_point": str, "assessment_text": str,}'
        auto_sysText = \
"""
----- Your Role -----
You will evaluate the necessity of continuing execution and the response evaluation based on the conversation history, the last user request, and the AI response.
Please provide your answer in the following JSON schema format.
'{"continue": str, "result_point": str, "assessment_text": str,}'
""" + '\n\n'
        auto_reqText = \
"""
----- Your Task -----
For the necessity of continued execution, respond with "continue" using the options "no," "yes," or "stop." (Example: yes)
Evaluate the response with "result_point" based on the achievement rate in relation to the user's request. (Example: 30)
Also, please provide the reason for your evaluation with "assessment_text." (Example: The response only addressed the main logic in response to a request for a working source code.)
Respond according to the following criteria:
1) If the user's request has been met, respond with continue=no, result_point=achievement rate, assessment_text=reason for evaluation.
2) If it seems to be in the middle of processing and the user has entered a new request saying "Please continue processing appropriately," and it seems possible to continue processing appropriately, respond with continue=yes, result_point=achievement rate, assessment_text=reason for evaluation.
3) In other cases or when continued execution is deemed difficult, respond with continue=stop, result_point=achievement rate, assessment_text=reason for evaluation.
""" + '\n\n'

        # ユーザー要求
        auto_inpText = ''
        if (len(old_history) > 2):
            auto_inpText = '----- 会話履歴 -----' + '\n'
            for m in range(len(old_history) - 1):
                role    = str(old_history[m].get('role', ''))
                content = str(old_history[m].get('content', ''))
                name    = str(old_history[m].get('name', ''))
                if (role != 'system'):
                    # 全てユーザーメッセージにて処理
                    if (name is None) or (name == ''):
                        auto_inpText += '(' + role + ')' + '\n'
                        auto_inpText += content + '\n\n'
            auto_inpText += '----- 最後のユーザー入力 -----' + '\n'
        auto_inpText += inpText + '\n\n'

        # 実行ループ
        n = 0
        while (n < int(self.auto_continue)):

            # GPT
            n += 1
            self.print(session_id, f" Assistant : { nick_name.lower() }, { model_name }, pass={ n }, ")

            # Assistant
            res_text2, res_path2, res_files2, nick_name, model_name, res_history = \
                self.run_assistant(chat_class=chat_class, model_select=model_select,
                                    nick_name=nick_name, model_name=model_name,
                                    session_id=session_id, history=res_history, function_modules=function_modules, 
                                    sysText=sysText, reqText=reqText, inpText=inpText,
                                    upload_files=upload_files, image_urls=image_urls,
                                    temperature=temperature, max_step=max_step, jsonSchema=jsonSchema, )
            
            if  (res_text2 is not None) \
            and (res_text2 != '') \
            and (res_text2 != '!'):
                res_text += res_text2
            if  (res_path2 is not None) \
            and (res_path2 != ''):
                res_path = res_path2
            if  (res_files2 is not None):
                if  (len(res_files2) != 0):
                    res_files.extend(res_files2)
                    upload_files.extend(res_files2)
                    res_files    = list(set(res_files))
                    upload_files = list(set(upload_files))

            # 実行検査
            if  (res_text is None) \
            or  (res_text == '') \
            or  (res_text == '!'): 
                break
            else:

                # GPT 評価判定
                check_inpText  = auto_inpText
                check_inpText += '----- ＡＩ応答 -----' + '\n'
                check_inpText += res_text2 + '\n\n'
                wk_json, wk_path, wk_files, wk_nick_name, wk_model_name, wk_history = \
                    self.run_gpt(chat_class='check', model_select='auto',
                                 nick_name=None, model_name=None,
                                 session_id='internal', history=[], function_modules={},
                                 sysText=auto_sysText, reqText=auto_reqText, inpText=check_inpText,
                                 upload_files=[], image_urls=[], jsonSchema=auto_jsonSchema, )

                continue_yn     = None
                result_point    = None
                assessment_text = None
                try:
                    args_dic        = json.loads(wk_json)
                    continue_yn     = args_dic.get('continue')
                    result_point    = args_dic.get('result_point')
                    assessment_text = args_dic.get('assessment_text')
                    self.print(session_id, f" Assistant : continue='{ continue_yn }', point={ result_point }, ({ wk_model_name })")
                    if (continue_yn != 'yes'):
                        self.print(session_id, assessment_text)
                except:
                    self.print(session_id, wk_json)

                # 継続判断
                if   (continue_yn == 'no') or (str(result_point) == '100'):
                    self.print(session_id, ' Assistant : completed OK !')
                    break
                elif (continue_yn != 'yes') \
                and  (continue_yn != 'no'):
                    self.print(session_id, ' Assistant : stop !')
                    break
                else:
                    if (n < int(self.auto_continue)):
                        reqText = ''
                        inpText = ''
                        if (continue_yn == 'yes'):
                            inpText += assessment_text + '\n'
                        inpText += '適切に判断して処理を継続してください' + '\n'
                        self.print(session_id, ' Assistant : auto continue,')
                        self.print(session_id, inpText)
                    else:
                        self.print(session_id, ' Assistant : auto continue exit !')

        # ファイル削除
        if  (self.work_upload_ids   is not None) \
        and (self.work_assistant_id is not None) \
        and (self.work_assistant_name is not None):
            res = self.threadFile_reset(session_id     = session_id,
                                        upload_ids     = self.work_upload_ids,
                                        assistant_id   = self.work_assistant_id,
                                        assistant_name = self.work_assistant_name, )

        return res_text, res_path, res_files, nick_name, model_name, res_history



    def chatBot(self, chat_class='auto', model_select='auto',
                session_id='admin', history=[], function_modules={},
                sysText=None, reqText=None, inpText='こんにちは', 
                filePath=[],
                temperature=0.8, max_step=10, jsonSchema=None,
                inpLang='ja-JP', outLang='ja-JP', ):

        # 戻り値
        res_text        = ''
        res_path        = ''
        res_files       = []
        nick_name       = None
        model_name      = None
        res_history     = history

        if (sysText is None) or (sysText == ''):
            sysText = 'あなたは美しい日本語を話す賢いアシスタントです。'
        if (inpText is None) or (inpText == ''):
            inpText = reqText
            reqText = None

        if (self.bot_auth is None):
            self.print(session_id, 'ChatGPT: Not Authenticate Error !')
            return res_text, res_path, res_files, nick_name, model_name, res_history

        # ファイル分離
        upload_files    = []
        image_urls      = []
        try:
            upload_files, image_urls = self.files_check(filePath=filePath, )
        except Exception as e:
            print(e)

        # チャットクラス 指定
        if (self.gpt_a_nick_name.lower()[:2] == 'o1'):
            chat_class = 'chat'
        if (chat_class == 'auto'):
            if (self.gpt_a_nick_name != ''):
                if (inpText.strip()[:len(self.gpt_a_nick_name)+1].lower() == (self.gpt_a_nick_name.lower() + ',')):
                    if (self.gpt_a_enable == True):
                        chat_class = 'chat'
            if (self.gpt_b_nick_name != ''):
                if (inpText.strip()[:len(self.gpt_b_nick_name)+1].lower() == (self.gpt_b_nick_name.lower() + ',')):
                    if (self.gpt_b_enable == True):
                        chat_class = 'chat'
            if (self.gpt_v_nick_name != ''):
                if (inpText.strip()[:len(self.gpt_v_nick_name)+1].lower() == (self.gpt_v_nick_name.lower() + ',')):
                    if (self.gpt_v_enable == True):
                        if  (len(image_urls) > 0) \
                        and (len(image_urls) == len(upload_files)):
                            chat_class = 'vision'
            if (self.gpt_x_nick_name != ''):
                if (inpText.strip()[:len(self.gpt_x_nick_name)+1].lower() == (self.gpt_x_nick_name.lower() + ',')):
                    if (self.gpt_x_enable == True):
                            chat_class = 'assistant'

        if (chat_class == 'auto'):
            if   (inpText.strip()[:5].lower() == ('riki,')):
                chat_class = 'assistant'
            elif (inpText.strip()[:7].lower() == ('vision,')):
                chat_class = 'vision'
            elif (inpText.strip()[:10].lower() == ('assistant,')):
                chat_class = 'assistant'
            elif (inpText.strip()[:7].lower() == ('openai,')):
                chat_class = 'chat'
            elif (inpText.strip()[:6].lower() == ('azure,')):
                chat_class = 'chat'
            elif (inpText.strip()[:7].lower() == ('claude,')):
                chat_class = 'chat'
            elif (inpText.strip()[:7].lower() == ('gemini,')):
                chat_class = 'chat'
            elif (inpText.strip()[:6].lower() == ('local,')):
                chat_class = 'chat'

        # ChatGPT
        if  ((chat_class != 'assistant') \
        and  (chat_class != 'コード生成') \
        and  (chat_class != 'コード実行') \
        and  (chat_class != '文書検索') \
        and  (chat_class != '複雑な会話') \
        and  (chat_class != 'アシスタント') \
        and  (model_select != 'x')):

            #try:
                res_text, res_path, res_files, nick_name, model_name, res_history = \
                    self.run_gpt(chat_class=chat_class, model_select=model_select,
                                 nick_name=nick_name, model_name=model_name,
                                 session_id=session_id, history=res_history, function_modules=function_modules,
                                 sysText=sysText, reqText=reqText, inpText=inpText,
                                 upload_files=upload_files, image_urls=image_urls,
                                 temperature=temperature, max_step=max_step, jsonSchema=jsonSchema, )
            #except Exception as e:
            #    print(e)

        # Assistant
        else:
            #try:
                res_text, res_path, res_files, nick_name, model_name, res_history = \
                    self.auto_assistant(chat_class=chat_class, model_select=model_select,
                                        nick_name=nick_name, model_name=model_name,
                                        session_id=session_id, history=res_history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText,
                                        upload_files=upload_files, image_urls=image_urls,
                                        temperature=temperature, max_step=max_step, jsonSchema=jsonSchema, )
            #except Exception as e:
            #    print(e)

        # 文書成形
        if (res_text.strip() == ''):
            res_text = '!'

        return res_text, res_path, res_files, nick_name, model_name, res_history



if __name__ == '__main__':

        #openaiAPI = speech_bot_openai.ChatBotAPI()
        openaiAPI = ChatBotAPI()

        api_type = openai_key.getkey('chatgpt','openai_api_type')
        print(api_type)

        log_queue = queue.Queue()
        res = openaiAPI.init(log_queue=log_queue, )

        if (api_type != 'azure'):
            res = openaiAPI.authenticate('chatgpt',
                            api_type,
                            openai_key.getkey('chatgpt','openai_default_gpt'), openai_key.getkey('chatgpt','openai_default_class'),
                            openai_key.getkey('chatgpt','openai_auto_continue'),
                            openai_key.getkey('chatgpt','openai_max_step'), openai_key.getkey('chatgpt','openai_max_session'),
                            openai_key.getkey('chatgpt','openai_organization'), openai_key.getkey('chatgpt','openai_key_id'),
                            openai_key.getkey('chatgpt','azure_endpoint'), openai_key.getkey('chatgpt','azure_version'), openai_key.getkey('chatgpt','azure_key_id'),
                            openai_key.getkey('chatgpt','gpt_a_nick_name'),
                            openai_key.getkey('chatgpt','gpt_a_model1'), openai_key.getkey('chatgpt','gpt_a_token1'),
                            openai_key.getkey('chatgpt','gpt_a_model2'), openai_key.getkey('chatgpt','gpt_a_token2'),
                            openai_key.getkey('chatgpt','gpt_a_model3'), openai_key.getkey('chatgpt','gpt_a_token3'),
                            openai_key.getkey('chatgpt','gpt_b_nick_name'),
                            openai_key.getkey('chatgpt','gpt_b_model1'), openai_key.getkey('chatgpt','gpt_b_token1'),
                            openai_key.getkey('chatgpt','gpt_b_model2'), openai_key.getkey('chatgpt','gpt_b_token2'),
                            openai_key.getkey('chatgpt','gpt_b_model3'), openai_key.getkey('chatgpt','gpt_b_token3'),
                            openai_key.getkey('chatgpt','gpt_b_length'),
                            openai_key.getkey('chatgpt','gpt_v_nick_name'),
                            openai_key.getkey('chatgpt','gpt_v_model'), openai_key.getkey('chatgpt','gpt_v_token'),
                            openai_key.getkey('chatgpt','gpt_x_nick_name'),
                            openai_key.getkey('chatgpt','gpt_x_model1'), openai_key.getkey('chatgpt','gpt_x_token1'),
                            openai_key.getkey('chatgpt','gpt_x_model2'), openai_key.getkey('chatgpt','gpt_x_token2'),
                            )
        else:
            res = openaiAPI.authenticate('chatgpt',
                            api_type,
                            openai_key.getkey('chatgpt','openai_default_gpt'), openai_key.getkey('chatgpt','openai_default_class'),
                            openai_key.getkey('chatgpt','openai_auto_continue'),
                            openai_key.getkey('chatgpt','openai_max_step'), openai_key.getkey('chatgpt','openai_max_session'),
                            openai_key.getkey('chatgpt','openai_organization'), openai_key.getkey('chatgpt','openai_key_id'),
                            openai_key.getkey('chatgpt','azure_endpoint'), openai_key.getkey('chatgpt','azure_version'), openai_key.getkey('chatgpt','azure_key_id'),
                            openai_key.getkey('chatgpt','azure_a_nick_name'),
                            openai_key.getkey('chatgpt','azure_a_model1'), openai_key.getkey('chatgpt','azure_a_token1'),
                            openai_key.getkey('chatgpt','azure_a_model2'), openai_key.getkey('chatgpt','azure_a_token2'),
                            openai_key.getkey('chatgpt','azure_a_model3'), openai_key.getkey('chatgpt','azure_a_token3'),
                            openai_key.getkey('chatgpt','azure_b_nick_name'),
                            openai_key.getkey('chatgpt','azure_b_model1'), openai_key.getkey('chatgpt','azure_b_token1'),
                            openai_key.getkey('chatgpt','azure_b_model2'), openai_key.getkey('chatgpt','azure_b_token2'),
                            openai_key.getkey('chatgpt','azure_b_model3'), openai_key.getkey('chatgpt','azure_b_token3'),
                            openai_key.getkey('chatgpt','azure_b_length'),
                            openai_key.getkey('chatgpt','azure_v_nick_name'),
                            openai_key.getkey('chatgpt','azure_v_model'), openai_key.getkey('chatgpt','azure_v_token'),
                            openai_key.getkey('chatgpt','azure_x_nick_name'),
                            openai_key.getkey('chatgpt','azure_x_model1'), openai_key.getkey('chatgpt','azure_x_token1'),
                            openai_key.getkey('chatgpt','azure_x_model2'), openai_key.getkey('chatgpt','azure_x_token2'),
                            )
        print('authenticate:', res, )
        if (res == True):
            
            function_modules = {}
            filePath         = []

            if True:
                import    speech_bot_function
                botFunc = speech_bot_function.botFunction()

                res, msg = botFunc.functions_load(
                    functions_path='_extensions/function/', secure_level='low', )
                if (res != True) or (msg != ''):
                    print(msg)
                    print()

                for key, module_dic in botFunc.function_modules.items():
                    if (module_dic['onoff'] == 'on'):
                        function_modules[key] = module_dic

            if True:
                sysText = None
                reqText = ''
                inpText = 'おはようございます。'
                filePath = []
                print('[Request]')
                print(reqText, inpText )
                print()
                res_text, res_path, res_files, res_name, res_api, openaiAPI.history = \
                    openaiAPI.chatBot(  chat_class='chat', model_select='auto', 
                                        session_id='guest1', history=openaiAPI.history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText, filePath=filePath,
                                        inpLang='ja', outLang='ja', )
                print()
                print('[' + res_name + '] (' + res_api + ')' )
                print('', res_text)
                print()

            if True:
                sysText = None
                reqText = ''
                inpText = '今日は何月何日？'
                filePath = []
                print('[Request]')
                print(reqText, inpText )
                print()
                res_text, res_path, res_files, res_name, res_api, openaiAPI.history = \
                    openaiAPI.chatBot(  chat_class='chat', model_select='auto', 
                                        session_id='admin', history=openaiAPI.history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText, filePath=filePath,
                                        inpLang='ja', outLang='ja', )
                print()
                print('[' + res_name + '] (' + res_api + ')' )
                print('', res_text)
                print()

            if True:
                sysText = None
                reqText = ''
                inpText = 'この画像はなんだと思いますか？'
                filePath = ['_icons/dog.jpg', '_icons/kyoto.png']
                print()
                print('[Request]')
                print(reqText, inpText )
                print()
                res_text, res_path, res_files, res_name, res_api, openaiAPI.history = \
                    openaiAPI.chatBot(  chat_class='vision', model_select='auto', 
                                        session_id='admin', history=openaiAPI.history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText, filePath=filePath,
                                        inpLang='ja', outLang='ja', )
                print()
                print('[' + res_name + '] (' + res_api + ')' )
                print('', res_text)
                print()

            if True:
                sysText = None
                reqText = ''
                inpText = 'riki,日本の主要３都市の天気？'
                filePath = []
                print('[Request]')
                print(reqText, inpText )
                print()
                res_text, res_path, res_files, res_name, res_api, openaiAPI.history = \
                    openaiAPI.chatBot(  chat_class='auto', model_select='auto', 
                                        session_id='admin', history=openaiAPI.history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText, filePath=filePath,
                                        inpLang='ja', outLang='ja', )
                print()
                print('[' + res_name + '] (' + res_api + ')' )
                print('', res_text)
                print()

            if True:
                sysText = None
                reqText = ''
                inpText = 'riki,この画像はなんだと思いますか？'
                filePath = ['_icons/dog.jpg', '_icons/kyoto.png']
                print()
                print('[Request]')
                print(reqText, inpText )
                print()
                res_text, res_path, res_files, res_name, res_api, openaiAPI.history = \
                    openaiAPI.chatBot(  chat_class='auto', model_select='auto', 
                                        session_id='admin', history=openaiAPI.history, function_modules=function_modules,
                                        sysText=sysText, reqText=reqText, inpText=inpText, filePath=filePath,
                                        inpLang='ja', outLang='ja', )
                print()
                print('[' + res_name + '] (' + res_api + ')' )
                print('', res_text)
                print()

            if False:
                print('[History]')
                for h in range(len(openaiAPI.history)):
                    print(openaiAPI.history[h])
                openaiAPI.history = []

            if False:
                res, msg = botFunc.functions_unload()
                if (res != True) or (msg != ''):
                    print(msg)
                    print()


