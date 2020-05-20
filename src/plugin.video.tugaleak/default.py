# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2
import json
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import time
import datetime
from urlparse import parse_qsl

addon = xbmcaddon.Addon("plugin.video.tugaleak")
__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])
__icon__ = addon.getAddonInfo('icon')
__fanart__ = addon.getAddonInfo('fanart')

ERROR_MESSAGE = {
    'badToken': 'EN: You will need to register a free account and subscribe in www.tugaleak.com/register\n'
                'PT: Precisas de te registar gratuitamente em www.tugaleak.com/register e inscrever-te para teres acesso.',
    'InvalidVideo': 'VIDEO NOT WORKING?, PLEASE REPORT IT.\n'
                    'www.tugaleak.com/video'
}
username = ''
password = ''


def log(message):
    xbmc.log('Tugaleak : {0}'.format(message))
    xbmcgui.Dialog().ok('Log', message)


def notify_api_error(error):
    if error and error.get('status', False):
        error_code = error['status']
    else:
        error_code = 'unknown'

    if error_code == 'error':
        title = 'Sign-up / Subscrição'
        line1 = ERROR_MESSAGE['badToken']
        line2 = ''
        if xbmcgui.Dialog().yesno(title, line1, line2):
            authorize()
        return False
    else:
        return notify_error(ERROR_MESSAGE.get(error_code, "API error: {0}".format('Api Request Failed!')))


def notify_error(message, time=5000):
    xbmcgui.Dialog().notification("Tugaleak Error", message, icon=__icon__, time=time)
    return False


def notify_message(message, time=5000):
    xbmcgui.Dialog().notification("Tugaleak", message, icon=__icon__, time=time)
    return False


def reset_authorization():
    addon.setSetting('username', '')
    addon.setSetting('password', '')


def authorize():
    reset_authorization()

    addon.openSettings()
    username = addon.getSetting('username')
    password = addon.getSetting('password')

    url = 'https://tugaleak.com/kodi-api/api.php'
    data = {'command': 'verify', 'username': username, 'password': password}
    rslt = request(url, data)

    if rslt['statusCode'] != 200:
        return notify_api_error(rslt)

    if rslt['status'] == 'error':
        return notify_message('Authorization Failed!')

    addon.setSetting('username', username)
    addon.setSetting('password', password)

    notify_message('Successfully Authorized!')
    return list_files('categories', '0', '0')


def url_resolve(video_url):
    try:
        site_url = video_url
        data = {}
        html_page = ''
        if 'https://mixdrop.co' in video_url:
            site_url = video_url.replace('https://mixdrop.co/f', 'https://mixdrop.co/e')
            data['server_type'] = 'mixdrop'
            html_page = get_html(site_url)
        elif 'https://uptostream.com' in video_url:
            api_url = site_url.replace('https://uptostream.com/',
                                       'https://uptostream.com/api/streaming/source/get?token=null&file_code=')
            api_reply = request(api_url)
            data['server_type'] = 'uptostream'
            if api_reply['message'] != 'Success':
                log(ERROR_MESSAGE['InvalidVideo'])
                return
            html_page = api_reply['data']['sources']
        elif 'https://streamz.cc' in video_url:
            data['server_type'] = 'streamz.cc'
            html_page = get_html(site_url)

        resolve_server_url = 'http://45.147.228.210:7777/get_playable_url'
        data['html_page'] = html_page
        rslt = request(resolve_server_url, data)
        if rslt['status'] != 'success':
            log(ERROR_MESSAGE['InvalidVideo'])
            return

        mp4_url = rslt['data']

        listing = []
        infoLabels = {
            'title': 'PLAY VIDEO'
        }
        li = xbmcgui.ListItem(label='Video Play')
        li.setInfo('video', infoLabels)
        li.setProperty('fanart_image', __fanart__)
        li.setProperty('IsPlayable', 'true')
        is_folder = False
        listing.append((mp4_url, li, is_folder))

        xbmcplugin.setContent(__handle__, 'movies')
        xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
        xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.endOfDirectory(__handle__)
    except:
        log(ERROR_MESSAGE['InvalidVideo'])
        return



def list_files(folder_id, id, server):
    username = addon.getSetting('username')
    password = addon.getSetting('password')

    api_url = 'https://tugaleak.com/kodi-api/api.php'
    data = {'command': folder_id,
            'username': username,
            'password': password,
            'id': id,
            'server': server}
    rslt = request(api_url, data)

    if rslt['statusCode'] != 200:
        return notify_api_error(rslt)

    if rslt['status'] == 'error':
        return notify_api_error(rslt)

    listing = []

    if folder_id == 'categories':
        for category_data in rslt['data']:
            infoLabels = {
                'title': category_data['vcat_title']
            }
            li = xbmcgui.ListItem(label=category_data['vcat_title'])
            li.setInfo('video', infoLabels)
            li.setProperty('fanart_image', __fanart__)
            url = '{0}?action=list_files&folder_id=videos&id={1}'.format(__url__, category_data['vcat_id'])
            is_folder = True
            listing.append((url, li, is_folder))
    elif folder_id == 'videos':
        for video_data in rslt['data']:
            infoLabels = {
                'title': video_data['v_title'],
                'genre': '12312312',
                'mediatype': 'video'
            }
            thumbnail = 'https://tugaleak.com/uploads/{0}'.format(video_data['v_thumbnail_medium'])
            arts = {'thumb': thumbnail,
                    'icon': thumbnail,
                    'fanart': thumbnail}
            li = xbmcgui.ListItem(label=video_data['v_title'], iconImage=thumbnail, thumbnailImage=thumbnail)
            li.setArt(arts)
            li.setInfo(type='video', infoLabels=infoLabels)
            li.setProperty('fanart_image', thumbnail)
            url = '{0}?action=list_files&folder_id=servers&id={1}'.format(__url__, video_data['v_id'])
            is_folder = True
            listing.append((url, li, is_folder))
    elif folder_id == 'servers':
        for server_data in rslt['data']:
            infoLabels = {
                'title': server_data['vbs_name']
            }
            li = xbmcgui.ListItem(label=server_data['vbs_name'])
            li.setInfo('video', infoLabels)
            li.setProperty('fanart_image', __fanart__)
            url = '{0}?action=list_files&folder_id=movies&id={1}&server={2}'.format(__url__, id,
                                                                                    server_data['vbo_server'])
            is_folder = True
            listing.append((url, li, is_folder))
    elif folder_id == 'movies':
        nCount = 1
        for movie_data in rslt['data']:
            title = 'Episode {0} ({1})'.format(nCount, movie_data['vbo_url'])
            infoLabels = {
                'title': title
            }
            li = xbmcgui.ListItem(label=title)
            li.setInfo('video', infoLabels)
            li.setProperty('fanart_image', __fanart__)
            # li.setProperty('IsPlayable', 'true')
            # is_folder = False
            is_folder = True
            # listing.append((movie_data['vbo_url'], li, is_folder))
            url = '{0}?action=url_resolve&video_url={1}'.format(__url__, movie_data['vbo_url'])
            listing.append((url, li, is_folder))
            nCount += 1

    xbmcplugin.setContent(__handle__, 'movies')
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
    xbmcplugin.endOfDirectory(__handle__)


def request(url, data=None, headers={}):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'}
    if data: data = urllib.urlencode(data)
    request = urllib2.Request(url, data=data, headers=headers)
    try:
        response = urllib2.urlopen(request)
        rslt = json.loads(response.read())
        rslt['statusCode'] = response.getcode()
    except urllib2.HTTPError as e:
        rslt = json.loads(e.read())
        rslt['statusCode'] = e.getcode()
        log('Request: Api Failed!')
    return rslt


def get_html(url, headers={}):
    headers[
        'User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
    request = urllib2.Request(url, headers=headers)

    try:
        response = urllib2.urlopen(request)
        rslt = response.read()
    except urllib2.HTTPError as e:
        rslt = e.read()
    return rslt


def router(paramstring):
    params = dict(parse_qsl(paramstring[1:]))
    action = params.get('action', 'list_files')
    if action == 'authorize':
        authorize()
    elif action == 'list_files':
        list_files(params.get('folder_id', 'categories'), params.get('id', '0'), params.get('server', '0'))
    elif action == 'url_resolve':
        url_resolve(params.get('video_url', ''))
    else:
        notify_error("Unknown plugin route")


router(sys.argv[2])
