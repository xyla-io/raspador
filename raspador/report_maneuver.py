import pandas as pd

from typing import Optional, Callable, List, Dict
from pathlib import Path
from subir import Uploader
from .maneuver import Maneuver, OrdnanceManeuver
from .pilot import Pilot

class ReportManeuver(OrdnanceManeuver[Pilot, pd.DataFrame]):
  def __init__(self, ordnance: Optional[pd.DataFrame]=None):
    super().__init__()
    self.no_ordnance_values = []
    if ordnance is not None:
      self.load(ordnance=ordnance)

class SaveReportManeuver(OrdnanceManeuver[Pilot, str]):
  report: Optional[pd.DataFrame]
  prefix: Optional[str]
  suffix: Optional[str]
  file_name: Optional[str]
  output_directory: Optional[str]
  include_report_index: bool

  def __init__(self, report: Optional[pd.DataFrame]=None, prefix: Optional[str]=None, suffix: Optional[str]=None, file_name: Optional[str]=None, output_directory: Optional[str]=None, include_report_index: bool=False):
    super().__init__()
    self.no_ordnance_values = []
    self.report = report
    self.prefix = prefix
    self.suffix = suffix
    self.file_name = file_name
    self.output_directory = output_directory
    self.include_report_index = include_report_index

  def attempt(self, pilot: Pilot):
    file_name = self.file_name
    if self.file_name is None:
      prefix = '' if self.prefix is None else self.prefix
      suffix = '' if self.suffix is None else self.suffix
      file_name = f'{prefix}{pilot.born.strftime("%Y-%m-%d_%H_%M_%S")}_{pilot.user.safe_file_name(pilot.description)}{suffix}.csv'
    output_directory_path = Path(__file__).parent.parent / 'output' / 'csv' if self.output_directory is None else Path(self.output_directory)
    output_path = output_directory_path / file_name

    if self.report is None:
      pilot.user.present_message(f'No data to save to \'{output_path}\'')
      return

    self.report.to_csv(str(output_path), index=self.include_report_index)
    pilot.user.present_message(f'Saved {len(self.report)} data rows to \'{output_path}\'')
    self.report = None
    self.load(output_path)

class LoadReportManeuver(ReportManeuver):
  report_path: Optional[str]
  detect_types: bool

  def __init__(self, report_path: Optional[str]=None, detect_types: bool=False):
    super().__init__()
    self.report_path = report_path
    self.detect_types = detect_types

  def attempt(self, pilot: Pilot):
    if not self.report_path:
      pilot.user.present_message('No path from which to load')
      return
    report_path = Path(self.report_path)
    read_args = {'dtype': str} if not self.detect_types else {}
    report = pd.read_csv(str(report_path), **read_args)
    pilot.user.present_message(f'Loaded {len(report)} data rows from \'{report_path}\'')
    self.load(report)

class ProcessReportManeuver(ReportManeuver):
  processor: Optional[Callable[[Optional[pd.DataFrame], Pilot, Callable[[Maneuver], Maneuver]], Optional[pd.DataFrame]]]

  def __init__(self, ordnance: Optional[pd.DataFrame]=None, processor: Optional[Callable[[Optional[pd.DataFrame], Pilot, Callable[[Maneuver], Maneuver]], Optional[pd.DataFrame]]]=None):
    super().__init__(ordnance=ordnance)
    self.processor = processor

  def attempt(self, pilot: Pilot, fly: Callable[[Maneuver], Maneuver]):
    if self.processor is None:
      pilot.user.present_message(f'No processor for {len(self.ordnance) if self.ordnance else 0} report rows')
      return
      
    report = self.deploy()
    pilot.user.present_message(f'Processing {len(report) if report else 0} report rows')
    processed_report = self.processor(report, pilot, fly)
    self.load(processed_report)
    pilot.user.present_message(f'Generated {len(processed_report) if processed_report is not None else 0} processed report rows')

class UploadReportManeuver(ReportManeuver):
  schema: Optional[str]
  table: Optional[str]
  confirm_upload: bool
  replace: bool
  merge_on_columns: List[str]
  column_types: Dict[str, any]

  def __init__(self, ordnance: Optional[pd.DataFrame], schema: Optional[str]=None, table: Optional[str]=None, confirm_upload: bool=True, replace: bool=False, merge_on_columns: List[str]=[], column_types: Dict[str, any]={}):
    super().__init__(ordnance=ordnance)
    self.schema = schema
    self.table = table
    self.confirm_upload = confirm_upload
    self.replace = replace
    self.merge_on_columns = merge_on_columns
    self.column_types = column_types

  def attempt(self, pilot: Pilot):
    if self.schema is None:
      pilot.user.present_message('No schema specified to upload data to')
      return

    if self.table is None:
      pilot.user.present_message('No table specified to upload data to in schema \'{self.schema}\'')
      return

    if self.ordnance is None or self.ordnance.empty:
      pilot.user.present_message(f'No data to upload to table\'{self.table}\' in schema \'{self.schema}\'')
      return
    
    if self.confirm_upload and not pilot.user.present_confirmation(f'Confirm {len(self.ordnance)} data rows upload to table \'{self.table}\' in schema \'{self.schema}\'', default_response=True):
      return

    uploader = Uploader()
    uploader.upload_data_frame(
      schema_name=self.schema,
      table_name=self.table,
      merge_column_names=self.merge_on_columns,
      data_frame=self.ordnance,
      column_type_transform_dictionary=self.column_types,
      replace=self.replace
    )
    pilot.user.present_message(f'Uploaded {len(self.ordnance)} rows to table\'{self.table}\' in schema \'{self.schema}\'')

class CollectReportManeuver(ReportManeuver):
  prefix: Optional[str]
  suffix: Optional[str]
  file_name: Optional[str]
  output_directory: Optional[str]
  raw_prefix: Optional[str]
  raw_suffix: Optional[str]
  raw_file_name: Optional[str]
  raw_output_directory: Optional[str]
  processor: Optional[Callable[[Optional[pd.DataFrame], Pilot, Callable[[Maneuver], Maneuver]], Optional[pd.DataFrame]]]
  schema: Optional[str]
  table: Optional[str]
  confirm_upload: bool
  replace: bool
  merge_on_columns: List[str]
  column_types: Dict[str, any]
  raw_path: Optional[str]
  processed_path: Optional[str]

  def __init__(self, ordnance: Optional[pd.DataFrame]=None, prefix: Optional[str]=None, suffix: Optional[str]=None, file_name: Optional[str]=None, output_directory: Optional[str]=None, raw_prefix: Optional[str]=None, raw_suffix: Optional[str]=None, raw_file_name: Optional[str]=None, raw_output_directory: Optional[str]=None, processor: Optional[Callable[[Optional[pd.DataFrame], Pilot, Callable[[Maneuver], Maneuver]], Optional[pd.DataFrame]]]=None, schema: Optional[str]=None, table: Optional[str]=None, confirm_upload: bool=True, replace: bool=False, merge_on_columns: List[str]=[], column_types: Dict[str, any]={}, raw_path: Optional[str]=None, processed_path: Optional[str]=None):
    super().__init__(ordnance=ordnance)
    self.prefix = prefix
    self.suffix = suffix
    self.file_name = file_name
    self.output_directory = output_directory
    self.raw_prefix = self.prefix if raw_prefix is None else raw_prefix
    if raw_suffix is None:
      self.raw_suffix = f'{self.suffix}_raw' if self.suffix else '_raw'
    else:
      self.raw_suffix = raw_suffix
    self.raw_file_name = raw_file_name
    self.raw_output_directory = self.output_directory if raw_output_directory is None else raw_output_directory
    self.processor = processor
    self.schema = schema
    self.table = table
    self.confirm_upload = confirm_upload
    self.replace = replace
    self.merge_on_columns = merge_on_columns
    self.column_types = column_types
    self.raw_path = raw_path
    self.processed_path = processed_path

  def attempt(self, pilot: Pilot, fly: Callable[[Maneuver], Maneuver]):
    if self.processed_path is None:
      if self.raw_path is None:
        raw_save_maneuver = SaveReportManeuver(
          report=self.deploy(),
          prefix=self.raw_prefix,
          suffix=self.raw_suffix,
          file_name=self.raw_file_name,
          output_directory=self.raw_output_directory
        )
        fly(raw_save_maneuver)
        raw_path = raw_save_maneuver.deploy()
      else:
        raw_path = self.raw_path

      raw_load_maneuver = LoadReportManeuver(report_path=raw_path)
      fly(raw_load_maneuver)
      self.load(raw_load_maneuver.deploy())

      process_maneuver = ProcessReportManeuver(
        ordnance=self.deploy(),
        processor=self.processor
      )
      fly(process_maneuver)
      self.load(process_maneuver.deploy())

      save_maneuver = SaveReportManeuver(
        report=self.deploy(),
        prefix=self.prefix,
        suffix=self.suffix,
        file_name=self.file_name,
        output_directory=self.output_directory
      )
      fly(save_maneuver)
      processed_path = save_maneuver.deploy()
    else:
      processed_path = self.processed_path

    load_maneuver = LoadReportManeuver(report_path=processed_path)
    fly(load_maneuver)
    self.load(load_maneuver.deploy())

    upload_maneuver = UploadReportManeuver(
      ordnance=self.deploy(),
      schema=self.schema,
      table=self.table,
      confirm_upload=self.confirm_upload,
      replace=self.replace,
      merge_on_columns=self.merge_on_columns,
      column_types=self.column_types
    )
    fly(upload_maneuver)
    self.load(upload_maneuver.deploy())

