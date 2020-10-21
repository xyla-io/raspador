import os
import click
import shlex
import subprocess

from typing import List
from datetime import datetime

log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'output', 'log', 'raspador.log')
def now():
  return datetime.now().astimezone().strftime('%a %b %d %H:%M:%S %Z %Y')

class RunContext:
  should_symlink: bool

  def __init__(self, should_symlink: bool):
    self.should_symlink = should_symlink

  def quote_command(self, run_args: str):
    return ' '.join(shlex.quote(a) for a in run_args)

@click.group()
@click.option('-s', '--symlink', 'should_symlink', is_flag=True)
@click.pass_context
def run(ctx: any, should_symlink: bool):
  ctx.obj = RunContext(should_symlink=should_symlink)

@run.command()
@click.option('-c/-C', '--cache/--no-cache', 'use_cache', is_flag=True, default=True)
@click.pass_obj
def build(context: RunContext, use_cache: bool):
  run_args = [
    'docker',
    'build',
    *([] if use_cache else ['--no-cache']),
    '-t', 'raspador',
    '--build-arg', f'SYMLINK={"true" if context.should_symlink else "false"}',
    '.'
  ]
  print(context.quote_command(run_args=run_args))
  subprocess.call(args=run_args)

@run.command()
@click.option('--shell', 'shell', is_flag=True)
@click.option('--monitor/--no-monitor', 'monitor', default=True)
@click.option('-i/-I', '--interactive/--no-interactive', 'is_interactive', default=True)
@click.option('-p', '--port', 'port', type=int, default=4000)
@click.option('-m', '--memory', 'memory', type=str, default='1g')
@click.option('--shared-memory', 'shared_memory', type=str, default='2g')
@click.option('--log', 'should_log', is_flag=True)
@click.argument('scrapeargs', nargs=-1)
@click.pass_obj
def scrape(context: RunContext, shell: bool, monitor: bool, is_interactive: bool, port: int, memory: str, shared_memory: str, should_log: bool, scrapeargs: List[str]):
  if monitor:
    if '--monitor' not in scrapeargs:
      scrapeargs = ('--monitor', *scrapeargs)
    subprocess.call(['open', 'monitor_docker.html'])
  if should_log:
    with open(log_path, 'a+') as f:
      f.write(f'Raspador started run at {now()} with args: {" ".join(scrapeargs)}\n')
  symlink_args = ['-v', f'{os.path.dirname(os.path.realpath(__file__))}:/dockerhost/app'] if context.should_symlink else []
  interactive_args = ['-it'] if is_interactive else []
  run_args = [
    'docker',
    'run',
    '--rm',
    '--privileged',
    '--memory', memory,
    '--shm-size', shared_memory,
    '-p', f'{port}:{port}',
    *symlink_args,
    *interactive_args,
    'raspador',
    'bash',
  ]
  shell_args = [
    '/usr/src/app/run.sh',
    *scrapeargs,
  ]
  if shell:
    print(f'{context.quote_command(run_args=run_args)}\n{context.quote_command(run_args=shell_args)}')
  else:
    print(context.quote_command(run_args=run_args + shell_args))
  args = run_args if shell else run_args + shell_args
  return_code = subprocess.call(args=args)
  result = 'finished' if return_code == 0 else 'failed'
  if should_log:
    with open(log_path, 'a+') as f:
      f.write(f'Raspador {result} run at {now()} with args: {" ".join(scrapeargs)}\n')

if __name__ == '__main__':
  run()
