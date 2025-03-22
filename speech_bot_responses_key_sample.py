#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ------------------------------------------------
# COPYRIGHT (C) 2014-2025 Mitsuo KONDOU.
# This software is released under the not MIT License.
# Permission from the right holder is required for use.
# https://github.com/konsan1101
# Thank you for keeping the rules.
# ------------------------------------------------

def getkey(api, key):

    # responses チャットボット
    if (api == 'responses'):
        print('speech_bot_responses_key.py')
        print('set your key!')
        if (key == 'responses_api_type'):
            return 'use responses api type'
        if (key == 'responses_default_gpt'):
            return 'use responses default gpt'
        if (key == 'responses_default_class'):
            return 'use chat default class'
        if (key == 'responses_auto_continue'):
            return 'use chat auto continue'
        if (key == 'responses_max_step'):
            return 'chat max step'
        if (key == 'responses_max_session'):
            return 'use max session'
        if (key == 'responses_max_wait_sec'):
            return 'chat max wait(sec)'

        if (key == 'openai_organization'):
            return 'your openai organization'
        if (key == 'openai_key_id'):
            return 'your openai key'

        if (key == 'azure_endpoint'):
            return 'your azure endpoint'
        if (key == 'azure_version'):
            return 'your azure version'
        if (key == 'azure_key_id'):
            return 'your azure key'

        if (key == 'responses_a_nick_name'):
            return 'your responses (a) nick name'
        if (key == 'responses_a_model'):
            return 'your responses (a) model'
        if (key == 'responses_a_token'):
            return 'your responses (a) token'
        if (key == 'responses_a_use_tools'):
            return 'your responses (a) use tools'

        if (key == 'responses_b_nick_name'):
            return 'your responses (b) nick name'
        if (key == 'responses_b_model'):
            return 'your responses (b) model'
        if (key == 'responses_b_token'):
            return 'your responses (b) token'
        if (key == 'responses_b_use_tools'):
            return 'your responses (b) use tools'

        if (key == 'responses_v_nick_name'):
            return 'your responses (v) nick name'
        if (key == 'responses_v_model'):
            return 'your responses (v) model'
        if (key == 'responses_v_token'):
            return 'your responses (v) token'
        if (key == 'responses_v_use_tools'):
            return 'your responses (v) use tools'

        if (key == 'responses_x_nick_name'):
            return 'your responses (x) nick name'
        if (key == 'responses_x_model'):
            return 'your responses (x) model'
        if (key == 'responses_x_token'):
            return 'your responses (x) token'
        if (key == 'responses_x_use_tools'):
            return 'your responses (x) use tools'

    return False


