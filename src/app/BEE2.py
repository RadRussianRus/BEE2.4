"""Run the BEE2."""
import trio

from BEE2_config import GEN_OPTS, get_package_locs
from app import gameMan, UI, music_conf, logWindow, img, TK_ROOT, DEV_MODE, tk_error, sound
import loadScreen
import packages
import utils
import srctools.logger

LOGGER = srctools.logger.get_logger('BEE2')
APP_NURSERY: trio.Nursery

DEFAULT_SETTINGS = {
    'Directories': {
        'package': 'packages/',
    },
    'General': {
        'preserve_BEE2_resource_dir': '0',
        'allow_any_folder_as_game': '0',
        'play_sounds': '1',
        'palette_save_settings': '0',
        'splash_stay_ontop': '1',
        'compact_splash': '0',

        # A token used to indicate the time the current cache/ was extracted.
        # This tells us whether to copy it to the game folder.
        'cache_time': '0',
        # We need this value to detect just removing a package.
        'cache_pack_count': '0',
    },
    'Debug': {
        # Log whenever items fallback to the parent style
        'log_item_fallbacks': '0',
        # Print message for items that have no match for a style
        'log_missing_styles': '0',
        # Print message for items that are missing ent_count values
        'log_missing_ent_count': '0',
        # Warn if a file is missing that a packfile refers to
        'log_incorrect_packfile': '0',

        # Determines if additional options are displayed.
        'development_mode': '0',

        # Show the log window on startup
        'show_log_win': '0',
        # The lowest level which will be shown.
        'window_log_level': 'INFO',
    },
}


async def init_app():
    """Initialise the application."""
    GEN_OPTS.load()
    GEN_OPTS.set_defaults(DEFAULT_SETTINGS)

    # Special case, load in this early so it applies.
    utils.DEV_MODE = GEN_OPTS.get_bool('Debug', 'development_mode')
    DEV_MODE.set(utils.DEV_MODE)

    LOGGER.debug('Starting loading screen...')
    loadScreen.main_loader.set_length('UI', 16)
    loadScreen.set_force_ontop(GEN_OPTS.get_bool('General', 'splash_stay_ontop'))
    loadScreen.show_main_loader(GEN_OPTS.get_bool('General', 'compact_splash'))

    # OS X starts behind other windows, fix that.
    if utils.MAC:
        TK_ROOT.lift()

    logWindow.HANDLER.set_visible(GEN_OPTS.get_bool('Debug', 'show_log_win'))
    logWindow.HANDLER.setLevel(GEN_OPTS['Debug']['window_log_level'])

    LOGGER.debug('Loading settings...')

    UI.load_settings()

    gameMan.load()
    gameMan.set_game_by_name(
        GEN_OPTS.get_val('Last_Selected', 'Game', ''),
        )
    gameMan.scan_music_locs()

    LOGGER.info('Loading Packages...')
    package_sys = await packages.load_packages(
        list(get_package_locs()),
        loader=loadScreen.main_loader,
        log_item_fallbacks=GEN_OPTS.get_bool(
            'Debug', 'log_item_fallbacks'),
        log_missing_styles=GEN_OPTS.get_bool(
            'Debug', 'log_missing_styles'),
        log_missing_ent_count=GEN_OPTS.get_bool(
            'Debug', 'log_missing_ent_count'),
        log_incorrect_packfile=GEN_OPTS.get_bool(
            'Debug', 'log_incorrect_packfile'),
        has_tag_music=gameMan.MUSIC_TAG_LOC is not None,
        has_mel_music=gameMan.MUSIC_MEL_VPK is not None,
    )
    loadScreen.main_loader.step('UI', 'pre_ui')
    APP_NURSERY.start_soon(img.init, package_sys)
    APP_NURSERY.start_soon(sound.sound_task)

    # Load filesystems into various modules
    music_conf.load_filesystems(package_sys.values())
    gameMan.load_filesystems(package_sys.values())
    UI.load_packages()
    loadScreen.main_loader.step('UI', 'package_load')
    LOGGER.info('Done!')

    # Check games for Portal 2's basemodui.txt file, so we can translate items.
    LOGGER.info('Loading Item Translations...')
    for game in gameMan.all_games:
        game.init_trans()

    LOGGER.info('Initialising UI...')
    await UI.init_windows()  # create all windows
    LOGGER.info('UI initialised!')

    loadScreen.main_loader.destroy()
    # Delay this until the loop has actually run.
    # Directly run TK_ROOT.lift() in TCL, instead
    # of building a callable.
    TK_ROOT.tk.call('after', 10, 'raise', TK_ROOT)


async def app_main() -> None:
    """The main loop for Trio."""
    global APP_NURSERY
    LOGGER.debug('Opening nursery...')
    try:
        async with trio.open_nursery() as nursery:
            APP_NURSERY = nursery
            await init_app()
            await trio.sleep_forever()
    except Exception as exc:
        tk_error(type(exc), exc, exc.__traceback__)
        raise


def done_callback(trio_main_outcome):
    """The app finished, quit."""
    from app import UI
    UI.quit_application()


def start_main() -> None:
    LOGGER.debug('Starting Trio loop.')
    trio.lowlevel.start_guest_run(
        app_main,
        run_sync_soon_threadsafe=TK_ROOT.after_idle,
        done_callback=done_callback,
    )
    TK_ROOT.mainloop()
