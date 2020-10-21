from pathlib import Path
from map_graph.map_graph_pilot import MapGraphPilot
from raspador import Maneuver, OrdnanceManeuver, MapGraphsEntryManeuver
from typing import Optional, Dict, List, Callable

class MapGraphScrapeManeuver(OrdnanceManeuver[MapGraphPilot, Optional[any]]):
  entry_key: Optional[str]
  map_context: Dict[str, any]
  map_context_urls: Optional[List[str]]

  def __init__(self, entry_key: Optional[str]=None, map_context: Dict[str, any]={}, map_context_urls: Optional[List[str]]=None):
    self.no_ordnance_values = []
    self.entry_key = entry_key
    self.map_context = map_context
    self.map_context_urls = map_context_urls
    super().__init__()

  def attempt(self, pilot: MapGraphPilot, fly: Callable[[Maneuver], Maneuver]):
    entry_key = pilot.entry_key if self.entry_key is None else self.entry_key
    map_context_urls = pilot.map_context_urls if self.map_context_urls is None else self.map_context_urls
    graph_maneuver = MapGraphsEntryManeuver(
      entry_key=entry_key,
      map_context=self.map_context,
      map_context_urls=map_context_urls
    )
    fly(graph_maneuver)
    self.load(graph_maneuver.deploy())

if __name__ == '__main__':
  enqueue_maneuver(MapGraphScrapeManeuver())
else:
  enqueue_maneuver(MapGraphScrapeManeuver())