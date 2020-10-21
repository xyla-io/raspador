import importlib

def import_credentials(name: str):
  try:
    module = importlib.import_module('credentials.local_{}_credentials'.format(name))
  except Exception:
    module = importlib.import_module('credentials.{}_credentials'.format(name))
  return getattr(module, '{}_credentials'.format(name))

raspador_credentials = import_credentials('raspador')
raspador_slackbot_credentials = import_credentials('raspador_slackbot')