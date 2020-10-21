import importlib
import json

def import_config(name: str):
  try:
    module = importlib.import_module('config.local_{}_config'.format(name))
  except Exception:
    module = importlib.import_module('config.{}_config'.format(name))
  return getattr(module, '{}_config'.format(name))

def import_json_config(name: str):
  try:
    with open(f'local_{name}.json') as f:
      return json.load(f)
  except FileExistsError:
    with open(f'{name}.json') as f:
      return json.load(f)

interactor_config = import_config('interactor')
mysql_config = import_config('mysql')
raspador_config = import_config('raspador')
sql_config = import_config('sql')
environment_config = import_json_config('configure')
user_config = import_config('user')