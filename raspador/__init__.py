"""
Automated scraping.
"""
from .base import MenuOption, ControlMode, ControlAction, Ordnance, OptionalOrdnance, XPath, BrowserElement
from .raspador import Raspador, OrdnanceRaspador, ReportRaspador, UploadReportRaspador
from .browser_interactor import BrowserInteractor
from .user_interactor import UserInteractor, Interaction
from .error import RaspadorError, RaspadorInputTimeoutError, RaspadorDidNotCompleteManuallyError, RaspadorCannotInteractError, RaspadorManeuverRequiredError, RaspadorInvalidManeuverError, RaspadorInvalidPositionError, RaspadorInteract, RaspadorSkip, RaspadorSkipOver, RaspadorSkipUp, RaspadorSkipToBreak, RaspadorQuit, RaspadorNoOrdnanceError, RaspadorElementError
from .pilot import Pilot, OrdnancePilot
from .parser import Parser, OrdnanceParser, SoupElementParser, SeekParser, Seeker, SoupSeeker, SoupIndexSeeker
from .maneuver import Maneuver, Position, NavigationManeuver, ClickXPathManeuver, SequenceManeuver, ClickXPathSequenceManeuver, OrdnanceManeuver, BreakManeuver, InteractManeuver, InteractQueueManeuver, FindElementManeuver, ClickSoupElementManeuver, ParseOrdnanceManeuver, SeekManeuver, ScriptQueueManeuver, ScriptManeuver, ElementManeuver, ClickElementManeuver, QuitManeuver
from .report_maneuver import ReportManeuver, SaveReportManeuver, LoadReportManeuver, ProcessReportManeuver, UploadReportManeuver, CollectReportManeuver
from .map_maneuver import MapGraphsEntryManeuver, MapGraphManeuver
from .bot_maneuver import BotManeuver
from .style import Styling, CustomStyling, Color, Font, Format, Styled, CustomStyled, Styleds
from .element import Element, ElementParser

from .explore_scraper import ExploreScraper