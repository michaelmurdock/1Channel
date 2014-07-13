import os
import re
import sys
import time
import datetime
import _strptime # fix bug in python import
import xbmc
import xbmcgui
import xbmcplugin
from addon.common.addon import Addon
from db_utils import DB_Connection
from pw_scraper import PW_Scraper
# from functools import wraps

db_connection = DB_Connection()

hours_list={}
hours_list['update_subscriptions'] = [2, 5, 10, 15, 24]
hours_list['movie_update'] = [2, 5, 10, 15, 24]
hours_list['backup_db'] = [12, 24, 168, 720]

DAY_NUMS = list('0123456')
DAY_CODES = ['M', 'T', 'W', 'H', 'F', 'Sa', 'Su']

_1CH = Addon('plugin.video.1channel')
pw_scraper = PW_Scraper(_1CH.get_setting("username"),_1CH.get_setting("passwd"))

def get_days_string_from_days(days):
    if days is None:
        days=''

    days_string=''
    fdow=int(_1CH.get_setting('first-dow'))
    adj_day_nums=DAY_NUMS[fdow:]+DAY_NUMS[:fdow]
    adj_day_codes=DAY_CODES[fdow:]+DAY_CODES[:fdow]
    all_days = ''.join(adj_day_codes)
    for i, day_num in enumerate(adj_day_nums):
        if day_num in days:
            days_string += adj_day_codes[i]
        
    if days_string==all_days:
        days_string='ALL'
        
    return days_string

def get_days_from_days_string(days_string):
    if days_string is None:
        days_string=''
        
    days_string=days_string.upper()
    days=''
    if days_string=='ALL':
        days='0123456'
    else:
        for i, day in enumerate(DAY_CODES):
            if day.upper() in days_string:
                days += DAY_NUMS[i]
                
    return days

def get_default_days():
    def_days= ['0123456', '', '0246']
    dow=datetime.datetime.now().weekday()
    def_days.append(str(dow))
    def_days.append(str(dow)+str((dow+1)%7))
    print def_days
    return def_days[int(_1CH.get_setting('sub-days'))]        

def format_label_tvshow(info):
    if 'premiered' in info:
        year = info['premiered'][:4]
    else:
        year = ''
    title = info['title']
    label = _1CH.get_setting('format-tvshow')
    # label = label.replace('{t}', title)
    # label = label.replace('{y}', year)
    # label = label.replace('{ft}', format_tvshow_title(title))
    # label = label.replace('{fy}', format_tvshow_year(year))

    label = re.sub('\{t\}', title, label)
    label = re.sub('\{y\}', year, label)
    label = re.sub('\{ft\}', format_tvshow_title(title), label)
    label = re.sub('\{fy\}', format_tvshow_year(year), label)
    return label


def format_tvshow_title(title):
    title_format = _1CH.get_setting('format-tvshow-title')
    label = re.sub('\{t\}', title, title_format)
    return label


def format_tvshow_year(year):
    if not year: return ''
    year_format = _1CH.get_setting('format-tvshow-year')
    label = re.sub('\{y\}', year, year_format)
    return label


def format_tvshow_episode(info):
    episode_format = _1CH.get_setting('format-tvshow-episode')
    label = re.sub('\{s\}', str(info['season']), episode_format)
    label = re.sub('\{e\}', str(info['episode']), label)
    label = re.sub('\{t\}', info['title'], label)
    label = re.sub('\{st\}', info['TVShowTitle'], label)
    return label


def format_label_sub(info):
    sub_format = _1CH.get_setting('format-tvshow-sub')
    label = format_label_tvshow(info)
    formatted_label = re.sub('\{L\}', label, sub_format)
    return formatted_label


def format_label_movie(info):
    if 'premiered' in info:
        year = info['premiered'][:4]
    else:
        year = ''
    label = _1CH.get_setting('format-movie')
    #label = label.replace('{t}', title)
    #label = label.replace('{y}', year)
    #label = label.replace('{ft}', format_movie_title(title))
    #label = label.replace('{fy}', format_movie_year(year))
    label = re.sub('\{t\}', info['title'], label)
    label = re.sub('\{y\}', year, label)
    label = re.sub('\{ft\}', format_movie_title(info['title']), label)
    label = re.sub('\{fy\}', format_movie_year(year), label)
    return label


def format_movie_title(title):
    title_format = _1CH.get_setting('format-movie-title')
    label = re.sub('\{t\}', title, title_format)
    return label


def format_movie_year(year):
    if not year: return ''
    year_format = _1CH.get_setting('format-movie-year')
    label = re.sub('\{y\}', year, year_format)
    return label


def format_label_source(info):
    label = _1CH.get_setting('format-source')
    label = re.sub('\{q\}', info['quality'], label)
    label = re.sub('\{h\}', info['host'], label)
    label = re.sub('\{v\}', str(info['views']), label)
    if info['multi-part']:
        parts = 'part 1'
    else:
        parts = ''
    label = re.sub('\{p\}', parts, label)
    if info['verified']: label = format_label_source_verified(label)
    return label


def format_label_source_verified(label):
    ver_format = _1CH.get_setting('format-source-verified')
    formatted_label = re.sub('\{L\}', label, ver_format)
    return formatted_label


def format_label_source_parts(info, part_num):
    label = _1CH.get_setting('format-source-parts')
    label = re.sub('\{q\}', info['quality'], label)
    label = re.sub('\{h\}', info['host'], label)
    label = re.sub('\{v\}', str(info['views']), label)
    parts = 'part %s' % part_num
    label = re.sub('\{p\}', parts, label)
    if info['verified']: label = format_label_source_verified(label)
    return label


def has_upgraded():
    old_version = _1CH.get_setting('old_version').split('.')
    new_version = _1CH.get_version().split('.')
    current_oct = 0
    for octant in old_version:
        if int(new_version[current_oct]) > int(octant):
            _1CH.log('New version found')
            return True
        current_oct += 1
    return False


def filename_from_title(title, video_type):
    if video_type == 'tvshow':
        filename = '%s S%sE%s.strm'
        filename = filename % (title, '%s', '%s')
    else:
        filename = '%s.strm' % title

    filename = re.sub(r'(?!%s)[^\w\-_\. ]', '_', filename)
    xbmc.makeLegalFilename(filename)
    return filename


def flush_cache():
        dlg = xbmcgui.Dialog()
        ln1 = 'Are you sure you want to '
        ln2 = 'delete the url cache?'
        ln3 = 'This will slow things down until rebuilt'
        yes = 'Keep'
        no = 'Delete'
        if dlg.yesno('Flush web cache', ln1, ln2, ln3, yes, no):
            db_connection.flush_cache()

class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % ( self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)
        self.setControls()

    def setControls(self):
        # set heading
        heading = "PrimeWire v%s" % (_1CH.get_version())
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        root = _1CH.get_path()
        faq_path = os.path.join(root, 'help.faq')
        f = open(faq_path)
        text = f.read()
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)


def website_is_integrated():
    enabled = _1CH.get_setting('site_enabled') == 'true'
    user = _1CH.get_setting('usename') is not None
    passwd = _1CH.get_setting('passwd') is not None
    return enabled and user and passwd

def rank_host(source):
    host = source['host']
    ranking = _1CH.get_setting('host-rank').split(',')
    host = host.lower()
    for tier in ranking:
        tier = tier.lower()
        if host in tier.split('|'):
            return ranking.index(tier) + 1
    return 1000


def refresh_meta(video_type, old_title, imdb, alt_id, year, new_title=''):
    from metahandler import metahandlers
    __metaget__ = metahandlers.MetaData()
    search_title = new_title if new_title else old_title
    if video_type == 'tvshow':
        api = metahandlers.TheTVDB()
        results = api.get_matching_shows(search_title)
        search_meta = []
        for item in results:
            option = {'tvdb_id': item[0], 'title': item[1], 'imdb_id': item[2], 'year': year}
            search_meta.append(option)

    else:
        search_meta = __metaget__.search_movies(search_title)
    print 'search_meta: %s' % search_meta

    option_list = ['Manual Search...']
    if search_meta:
        for option in search_meta:
            if 'year' in option:
                disptitle = '%s (%s)' % (option['title'], option['year'])
            else:
                disptitle = option['title']
            option_list.append(disptitle)
        dialog = xbmcgui.Dialog()
        index = dialog.select('Choose', option_list)

        if index == 0:
            refresh_meta_manual(video_type, old_title, imdb, alt_id, year)
        elif index > -1:
            new_imdb_id = search_meta[index - 1]['imdb_id']

            #Temporary workaround for metahandlers problem:
            #Error attempting to delete from cache table: no such column: year
            if video_type == 'tvshow': year = ''

            _1CH.log(search_meta[index - 1])
            __metaget__.update_meta(video_type, old_title, imdb, year=year)
            xbmc.executebuiltin('Container.Refresh')


def refresh_meta_manual(video_type, old_title, imdb, alt_id, year):
    keyboard = xbmc.Keyboard()
    if year:
        disptitle = '%s (%s)' % (old_title, year)
    else:
        disptitle = old_title
    keyboard.setHeading('Enter a title')
    keyboard.setDefault(disptitle)
    keyboard.doModal()
    if keyboard.isConfirmed():
        search_string = keyboard.getText()
        refresh_meta(video_type, old_title, imdb, alt_id, year, search_string)


def set_view(content, view_type):
    # set content type so library shows more views and info
    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)
    if _1CH.get_setting('auto-view') == 'true':
        view_mode = _1CH.get_setting(view_type)
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_mode)

    # set sort methods - probably we don't need all of them
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_PROGRAM_COUNT)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_GENRE)
        

def get_dir_size(start_path):
    print 'Calculating size of %s' % start_path
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for each_file in filenames:
            fpath = os.path.join(dirpath, each_file)
            total_size += os.path.getsize(fpath)
    print 'Calculated: %s' % total_size
    return total_size
        

def format_eta(seconds):
    minutes, seconds = divmod(seconds, 60)
    if minutes > 60:
        hours, minutes = divmod(minutes, 60)
        return "ETA: %02d:%02d:%02d " % (hours, minutes, seconds)
    else:
        return "ETA: %02d:%02d " % (minutes, seconds)

# returns true if user chooses to resume, else false
def get_resume_choice(url):
    question = 'Resume from %s' % (format_time(db_connection.get_bookmark(url)))
    return xbmcgui.Dialog().yesno('Resume?', question, '', '', 'Start from beginning', 'Resume')

# simple wrapper to avoid instantiating a db_connection in pw_scraper
def get_cached_url(url, cache_limit):
    return db_connection.get_cached_url(url, cache_limit)

# simple wrapper to avoid instantiating a db_connection in pw_scraper
def cache_url(url, body):
    return db_connection.cache_url(url,body)
    
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    if minutes > 60:
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)

# Run a task on startup. Settings and mode values must match task name
def do_startup_task(task):
    run_on_startup=_1CH.get_setting('auto-%s' % task)=='true' and _1CH.get_setting('%s-during-startup' % task) == 'true' 
    if run_on_startup and not xbmc.abortRequested:
        _1CH.log('Service: Running startup task [%s]' % (task))
        now = datetime.datetime.now()
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.1channel/?mode=%s)' % (task))
        _1CH.set_setting('%s-last_run' % (task), now.strftime("%Y-%m-%d %H:%M:%S.%f"))
    
# Run a recurring scheduled task. Settings and move values much match task name
def do_scheduled_task(task, isPlaying):
    now = datetime.datetime.now()
    if _1CH.get_setting('auto-%s' % task) == 'true':
        last_run = _1CH.get_setting('%s-last_run' % (task))
        hours = hours_list[task][int(_1CH.get_setting('%s-interval' % (task)))]
        last_run = datetime.datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S.%f")
        elapsed = now - last_run

        threshold = datetime.timedelta(hours=hours)
        #_1CH.log("Update Status on [%s]: %s of %s" % (task, elapsed, threshold))
        if elapsed > threshold:
            is_scanning = xbmc.getCondVisibility('Library.IsScanningVideo')
            if not is_scanning:
                during_playback = _1CH.get_setting('%s-during-playback' % (task))=='true'
                if during_playback or not isPlaying:
                    _1CH.log('Service: Running Scheduled Task: [%s]' % (task))
                    builtin = 'RunPlugin(plugin://plugin.video.1channel/?mode=%s)' % (task)
                    xbmc.executebuiltin(builtin)
                    _1CH.set_setting('%s-last_run' % task, now.strftime("%Y-%m-%d %H:%M:%S.%f"))
                else:
                    _1CH.log('Service: Playing... Busy... Postponing [%s]' % (task))
            else:
                _1CH.log('Service: Scanning... Busy... Postponing [%s]' % (task))

def get_adv_search_query(section):
    if section=='tv':
        header_text='Advanced TV Show Search'
    else:
        header_text='Advanced Movie Search'
    SEARCH_BUTTON = 200
    CANCEL_BUTTON = 201
    HEADER_LABEL=100
    ACTION_PREVIOUS_MENU = 10
    ACTION_BACK = 92
    CENTER_Y=6
    CENTER_X=2
    now = datetime.datetime.now()
    # allowed values have to be list of strings
    allowed_values={}
    allowed_values['month'] = [''] + [str(month) for month in xrange(1,13)]
    allowed_values['year'] = [''] +  [str(year) for year in xrange(1900,now.year+1)]
    allowed_values['decade'] =[''] + [str(decade) for decade in xrange(1900, now.year+1, 10)]
    allowed_values['genre'] = [''] + pw_scraper.get_genres()
    class AdvSearchDialog(xbmcgui.WindowXMLDialog):
        ypos=85
        gap=55
        params=[
                ('title', 30, ypos, 30, 450),
                ('tag', 30, ypos+gap, 30, 450),
                ('actor', 30, ypos+gap*2, 30, 450),
                ('director', 30, ypos+gap*3, 30, 450),
                ('country', 30, ypos+gap*4, 30, 450),
                ('genre', 30, ypos+gap*5, 30, 450),
                ('month', 30, ypos+gap*6, 30, 140),
                ('year', 185, ypos+gap*6, 30, 140),
                ('decade', 340, ypos+gap*6, 30, 140)]
        def onInit(self):
            self.query_controls=[]
            # add edits for title, tag, actor and director
            for i in xrange(9):
                self.query_controls.append(self.__add_editcontrol(self.params[i][1], self.params[i][2], self.params[i][3], self.params[i][4]))
                if i>0:
                    self.query_controls[i].controlUp(self.query_controls[i-1])
                    self.query_controls[i].controlLeft(self.query_controls[i-1])
                if i<9:
                    self.query_controls[i-1].controlDown(self.query_controls[i])
                    self.query_controls[i-1].controlRight(self.query_controls[i])
            
            search=self.getControl(SEARCH_BUTTON)
            cancel=self.getControl(CANCEL_BUTTON)
            self.query_controls[0].controlUp(cancel)
            self.query_controls[0].controlLeft(cancel)
            self.query_controls[-1].controlDown(search)
            self.query_controls[-1].controlRight(search)
            search.controlUp(self.query_controls[-1])
            search.controlLeft(self.query_controls[-1])
            cancel.controlDown(self.query_controls[0])
            cancel.controlRight(self.query_controls[0])
            header=self.getControl(HEADER_LABEL)
            header.setLabel(header_text)
        
        def onAction(self,action):
            #print 'Action: %s' %(action.getId())
            if action==ACTION_PREVIOUS_MENU or action==ACTION_BACK:
                self.close()

        def onControl(self,control):
            #print 'onControl: %s' % (control)
            pass
            
        def onFocus(self,control):
            #print 'onFocus: %s' % (control)
            pass
            
        def onClick(self, control):
            #print 'onClick: %s' %(control)
            if control==SEARCH_BUTTON:
                if not self.__validateFields():
                    return
                
                self.search=True
            if control==CANCEL_BUTTON:
                self.search=False
                
            if control==SEARCH_BUTTON or control==CANCEL_BUTTON:
                self.close()
                
        def get_result(self):
            return self.search
        
        def get_query(self):
            texts=[]
            for control in self.query_controls:
                if isinstance(control,xbmcgui.ControlEdit):
                    texts.append(control.getText())
                elif isinstance(control,xbmcgui.ControlList):
                    texts.append(control.getSelectedItem().getLabel())
                    
            params=[param[0] for param in self.params]
            query=dict(zip(params, texts))
            return query
        
        # returns True if everything validates, false otherwise
        def __validateFields(self):
            error=False
            all_values = ''.join([control.getText().strip() for control in self.query_controls])
            if all_values == '':
                error_string = 'Enter at least one criteria to search on.'
                error=True
            else:                
                # validate fields with allowed values
                valid_fields=['genre', 'month', 'year', 'decade']
                field_names=[param[0] for param in self.params]
                for field in valid_fields:
                    field_value=self.query_controls[field_names.index(field)].getText()
                    if field_value != '':
                        print field_value
                        if field_value not in allowed_values[field]:
                            error_string = '%s must be one of: %s' % (field.capitalize(), str(allowed_values[field][1:]).replace("'",""))
                            # override error string on year
                            if field == 'year':
                                error_string = 'Year must be a 4 digit number between %s and %s.' % (allowed_values[field][1], allowed_values[field][-1])
                            error=True
                            break
                        
            if error:
                _1CH.show_ok_dialog([error_string], title='PrimeWire')
            return not error
        
        # have to add edit controls programatically because getControl() (hard) crashes XBMC on them 
        def __add_editcontrol(self,x, y, height, width):
            temp=xbmcgui.ControlEdit(0,0,0,0,'', font='font12', textColor='0xFFFFFFFF', focusTexture='button-focus2.png', noFocusTexture='button-nofocus.png', _alignment=CENTER_Y|CENTER_X)
            temp.setPosition(x, y)
            temp.setHeight(height)
            temp.setWidth(width)
            self.addControl(temp)
            return temp

    dialog=AdvSearchDialog('AdvSearchDialog.xml', _1CH.get_path())
    dialog.doModal()
    if dialog.get_result():
        query=dialog.get_query()
        del dialog
        _1CH.log('Returning query of: %s' % (query)) 
        return query
    else:
        del dialog
        raise
