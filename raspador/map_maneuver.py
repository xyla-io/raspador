import json

from time import sleep
from jsoncomment import JsonComment
from typing import Optional, Dict, List, Callable, Union
from io_map import IOMap, IOMapKey, IOMapOption, IOMapGraph
from data_layer import locator_factory
from .pilot import Pilot
from .maneuver import Maneuver, OrdnanceManeuver

class MapGraphsEntryManeuver(OrdnanceManeuver[Pilot, Optional[any]]):
  entry_key: str
  map_context: Dict[str, any]
  map_context_urls: List[str]
  clear_registries: bool
  auto_register: bool
  register_identifiers: List[str]
  strict_json: bool

  def __init__(self, entry_key: str, map_context: Dict[str, any]={}, map_context_urls: List[str]=[], clear_registries: bool=False, auto_register: bool=True, register_identifiers: List[str]=[], strict_json: bool=False):
    self.no_ordnance_values = []
    self.entry_key = entry_key
    self.map_context = {**map_context}
    self.map_context_urls = [*map_context_urls]
    self.clear_registries = clear_registries
    self.auto_register = auto_register
    self.register_identifiers = [*register_identifiers]
    self.strict_json = strict_json
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'perform map graph {self.entry_key} from graphs {json.dumps(self.map_context, sort_keys=True)} and urls {", ".join(self.map_context_urls)}'

  def prepare_map_context(self) -> Dict[str, any]:
    map_context = {**self.map_context}
    for url in self.map_context_urls:
      locator = locator_factory(url=url)
      url_contents = locator.get()
      if isinstance(url_contents, bytes):
        url_contents = url_contents.decode()
      url_graphs = json.loads(url_contents) if self.strict_json else JsonComment().loads(url_contents)
      map_context.update(url_graphs)
    return map_context

  def attempt(self, pilot: Pilot, fly: Callable[[Maneuver], Maneuver]):
    map_context = self.prepare_map_context()
    with IOMap._local_registries(clear=self.clear_registries):
      previous_auto_register = IOMap.map_auto_register
      IOMap.map_auto_register = self.auto_register
      try:
        IOMap._register_context(map_context)
        entry_value = self[f'{IOMapKey.iocontext.value}.{self.entry_key}']
        key_maps = entry_value if isinstance(entry_value, list) else [{IOMapKey.iokeymap.value: f'{IOMapKey.iocontext.value}.{self.entry_key}'}]
        graph = MapGraphManeuver(
          key_maps=key_maps
        )
        fly(graph)
        output = graph.deploy()
        self.load(output)
      finally:
        IOMap.map_auto_register = previous_auto_register

class MapGraphManeuver(IOMapGraph, OrdnanceManeuver[Pilot, Optional[any]]):
  default_key_map: Dict[str, any]
  pause: float

  def __init__(self, key_maps: Union[List[any], Dict[str, any], str], input_keys: List[str]=[], output_keys: List[str]=[], private_keys: List[str]=[], default_key_map: Dict[str, any]={IOMapKey.options.value: {IOMapOption.expand_at_run.value: {}}}, pause: float=1, **kwargs):
    self.no_ordnance_values = []
    self.default_key_map = {**default_key_map}
    self.pause = pause
    super().__init__(
      key_maps=key_maps,
      input_keys=input_keys,
      output_keys=output_keys,
      private_keys=private_keys,
      **kwargs
    )
    OrdnanceManeuver.__init__(self)
    self.key_maps = list(map(lambda m: type(self)._merged_key_map(default_key_map, m), self.key_maps))
  
  def run_map(self, expanded_map: Dict[str, any]) -> Dict[str, any]:
    output = super().run_map(expanded_map=expanded_map)
    if self.pause > 0:
      sleep(self.pause)
    return output