import os

# workaround for bug in Python imports
import datetime
# noinspection PyUnresolvedReferences
import _strptime
# noinspection PyUnresolvedReferences
import time
import json

import xbmc
import xbmcgui
import xbmcaddon
import utils

hours_list = [2, 5, 10, 15, 24]

ADDON = xbmcaddon.Addon(id='plugin.video.1channel')

try:
    DB_NAME = ADDON.getSetting('db_name')
    DB_USER = ADDON.getSetting('db_user')
    DB_PASS = ADDON.getSetting('db_pass')
    DB_ADDR = ADDON.getSetting('db_address')

    if ADDON.getSetting('use_remote_db') == 'true' and \
                    DB_ADDR is not None and \
                    DB_USER is not None and \
                    DB_PASS is not None and \
                    DB_NAME is not None:
        import mysql.connector as database

        xbmc.log('PrimeWire: Service: Loading MySQL as DB engine')
        DB = 'mysql'
    else:
        xbmc.log('PrimeWire: Service: MySQL not enabled or not setup correctly')
        raise ValueError('MySQL not enabled or not setup correctly')
except:
    try:
        from sqlite3 import dbapi2 as database
        xbmc.log('PrimeWire: Service: Loading sqlite3 as DB engine')
    except:
        from pysqlite2 import dbapi2 as database
        xbmc.log('PrimeWire: Service: Loading pysqlite2 as DB engine')
    DB = 'sqlite'
    db_dir = os.path.join(xbmc.translatePath("special://database"), 'onechannelcache.db')

def ChangeWatched(imdb_id, video_type, name, season, episode, year='', watched=''):
    from metahandler import metahandlers

    metaget = metahandlers.MetaData(False)
    metaget.change_watched(video_type, name, imdb_id, season=season, episode=episode, year=year, watched=watched)

class Service(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self, *args, **kwargs)
        self.reset()

        self.last_run = 0
        self.DB = ''
        xbmc.log('PrimeWire: Service starting...')


    def reset(self):
        xbmc.log('PrimeWire: Service: Resetting...')
        win = xbmcgui.Window(10000)
        win.clearProperty('1ch.playing.title')
        win.clearProperty('1ch.playing.year')
        win.clearProperty('1ch.playing.imdb')
        win.clearProperty('1ch.playing.season')
        win.clearProperty('1ch.playing.episode')
        win.clearProperty('1ch.playing.url')

        self._totalTime = 999999
        self._lastPos = 0
        self.tracking = False
        self.video_type = ''
        self.win = xbmcgui.Window(10000)
        self.win.setProperty('1ch.playing', '')
        self.meta = ''
        self.video_url=''


    def onPlayBackStarted(self):
        xbmc.log('PrimeWire: Service: Playback started')
        meta = self.win.getProperty('1ch.playing')
        if meta: #Playback is ours
            xbmc.log('PrimeWire: Service: tracking progress...')
            self.tracking = True
            self.meta = json.loads(meta)
            self.video_type = 'tvshow' if 'episode' in self.meta else 'movie'
            if not 'year'    in self.meta: self.meta['year']    = ''
            if not 'imdb'    in self.meta: self.meta['imdb']    = None
            if not 'season'  in self.meta: self.meta['season']  = ''
            if not 'episode' in self.meta: self.meta['episode'] = ''
            self.video_url = self.win.getProperty('1ch.playing.url')

            self._totalTime=0
            while self._totalTime == 0:
                xbmc.sleep(1000)
                self._totalTime = self.getTotalTime()
                print "Total Time: %s"   % (self._totalTime)

    def onPlayBackStopped(self):
        xbmc.log('PrimeWire: Playback Stopped')
        #Is the item from our addon?
        if self.tracking:
            DBID = self.meta['DBID'] if 'DBID' in self.meta else None
            playedTime = int(self._lastPos)
            watched_values = [.7, .8, .9]
            min_watched_percent = watched_values[int(ADDON.getSetting('watched-percent'))]
            percent = int((playedTime / self._totalTime) * 100)
            pTime = utils.format_time(playedTime)
            tTime = utils.format_time(self._totalTime)
            xbmc.log('PrimeWire: Service: %s played of %s total = %s%%' % (pTime, tTime, percent))
            videotype = 'movie' if self.video_type == 'movie' else 'episode'
            if playedTime == 0 and self._totalTime == 999999:
                raise RuntimeError('XBMC silently failed to start playback')
            elif ((playedTime / self._totalTime) > min_watched_percent) and (
                        self.video_type == 'movie' or (self.meta['season'] and self.meta['episode'])):
                xbmc.log('PrimeWire: Service: Threshold met. Marking item as watched')
                # meta['DBID'] only gets set for strms in default.py
                if DBID:
                    if videotype == 'episode':
                        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": %s, "properties": ["playcount"]}, "id": 1}'
                        cmd = cmd %(DBID)
                        result = json.loads(xbmc.executeJSONRPC(cmd))
                        print result
                        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid": %s, "playcount": %s}, "id": 1}'
                        playcount = int(result['result']['episodedetails']['playcount']) + 1
                        cmd = cmd %(DBID, playcount)
                        result = xbmc.executeJSONRPC(cmd)
                        xbmc.log('PrimeWire: Marking episode .strm as watched: %s' %result)
                    if videotype == 'movie':
                        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": %s, "properties": ["playcount"]}, "id": 1}'
                        cmd = cmd %(DBID)
                        result = json.loads(xbmc.executeJSONRPC(cmd))
                        print result
                        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": %s, "playcount": %s}, "id": 1}'
                        playcount = int(result['result']['moviedetails']['playcount']) + 1
                        cmd = cmd %(DBID, playcount)
                        result = xbmc.executeJSONRPC(cmd)
                        xbmc.log('PrimeWire: Marking movie .strm as watched: %s' %result)
                video_title = self.meta['title'] if self.video_type == 'movie' else self.meta['TVShowTitle']
                ChangeWatched(self.meta['imdb'], videotype,video_title.strip(), self.meta['season'], self.meta['episode'], self.meta['year'], watched=7)
                utils.clear_bookmark(self.video_url)
            else:
                xbmc.log('PrimeWire: Service: Threshold not met. Setting bookmark on %s to %s seconds' % (self.video_url,playedTime))
                utils.set_bookmark(self.video_url,playedTime)
        self.reset()

    def onPlayBackEnded(self):
        xbmc.log('PrimeWire: Playback completed')
        self.onPlayBackStopped()
        
monitor = Service()
while not xbmc.abortRequested:
    if ADDON.getSetting('auto-update-subscriptions') == 'true':
        now = datetime.datetime.now()
        last_run = ADDON.getSetting('last_run')
        hours = hours_list[int(ADDON.getSetting('subscription-interval'))]

        last_run = datetime.datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S.%f")
        elapsed = now - last_run
        threshold = datetime.timedelta(hours=hours)
        #xbmc.log("Update Status: %s of %s" % (elapsed,threshold))
        if elapsed > threshold:
            is_scanning = xbmc.getCondVisibility('Library.IsScanningVideo')
            if not is_scanning:
                during_playback = ADDON.getSetting('during-playback')
                if during_playback == 'true' or not monitor.isPlaying():
                    xbmc.log('PrimeWire: Service: Updating subscriptions')
                    builtin = 'RunPlugin(plugin://plugin.video.1channel/?mode=update_subscriptions)'
                    xbmc.executebuiltin(builtin)
                    ADDON.setSetting('last_run', now.strftime("%Y-%m-%d %H:%M:%S.%f"))
                else:
                    xbmc.log('PrimeWire: Service: Playing... Busy... Postponing subscription update')
            else:
                xbmc.log('PrimeWire: Service: Scanning... Busy... Postponing subscription update')

    if monitor.tracking and monitor.isPlayingVideo():
        monitor._lastPos = monitor.getTime()

    xbmc.sleep(1000)
xbmc.log('PrimeWire: Service: shutting down...')
