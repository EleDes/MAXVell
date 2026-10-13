"""Database exploration remains bounded and cannot change the publication."""
from contextlib import redirect_stdout
from io import StringIO
import hashlib,json,tempfile,unittest
from pathlib import Path
from maxvell import models
from maxvell.cli import main
from maxvell.query import schema,sql

class QueryTest(unittest.TestCase):
    def test_schema_and_exact_target_query(self):
        self.assertEqual(schema()['tables']['model_catalog']['rows'],1363)
        result=sql('SELECT target,kind,cfm_bits FROM model_catalog WHERE target=? AND kind=?',['5M40ZE64C5','lut'])
        self.assertEqual(result['rows'],[{'target':'5M40ZE64C5','kind':'lut','cfm_bits':53248}])
        self.assertFalse(result['truncated'])
    def test_sql_cannot_write_attach_or_read_raw_blobs(self):
        before=hashlib.sha256(models.DATABASE.read_bytes()).digest()
        for statement in ('DELETE FROM metadata','PRAGMA query_only=OFF',"ATTACH DATABASE ':memory:' AS other",'SELECT * FROM model_blobs','SELECT * FROM sqlite_master','SELECT load_extension(?)','SELECT randomblob(1000000000)'):
            with self.subTest(statement=statement),self.assertRaisesRegex(ValueError,'Read-only query rejected'):
                sql(statement)
        self.assertEqual(hashlib.sha256(models.DATABASE.read_bytes()).digest(),before)
    def test_rows_and_output_size_are_bounded(self):
        result=sql('SELECT target,kind FROM model_catalog ORDER BY target,kind',limit=1)
        self.assertTrue(result['truncated']);self.assertEqual(result['row_count'],1)
        with self.assertRaisesRegex(ValueError,'byte bound'):sql('SELECT ? AS value',['x'*16384])
        with self.assertRaisesRegex(ValueError,'byte bound'):sql('SELECT ? AS value',['\u03bc'*3000])
        with self.assertRaisesRegex(ValueError,'limit'):sql('SELECT 1',limit=1001)
    def test_duplicate_columns_and_parameters_rejected(self):
        with self.assertRaisesRegex(ValueError,'aliases'):sql('SELECT 1 AS x,2 AS x')
        with self.assertRaisesRegex(ValueError,'JSON array'):sql('SELECT 1',{'x':1})
        with self.assertRaisesRegex(ValueError,'JSON array'):sql('SELECT 1',[{}])
        with self.assertRaisesRegex(ValueError,'64-bit'):sql('SELECT ?',[1<<100])
        with self.assertRaisesRegex(ValueError,'finite'):sql('SELECT ?',[float('inf')])
    def test_expensive_join_is_interrupted(self):
        with self.assertRaisesRegex(ValueError,'interrupted'):
            sql('SELECT COUNT(*) AS n FROM model_catalog a CROSS JOIN model_catalog b CROSS JOIN model_catalog c')
    def test_model_export_is_verified_and_complete(self):
        with tempfile.TemporaryDirectory() as temp,redirect_stdout(StringIO()) as output:
            out=Path(temp)/'usercode.json'
            self.assertEqual(main(['query','model','--target','5M40ZE64C5','--kind','usercode','--out',str(out)]),0)
            self.assertEqual(json.loads(out.read_text()),models.load('5M40ZE64C5','usercode')[0])
            self.assertTrue(json.loads(output.getvalue())['checksum_verified'])
    def test_cli_file_query_keeps_stdout_bounded(self):
        with tempfile.TemporaryDirectory() as temp,redirect_stdout(StringIO()) as output:
            out=Path(temp)/'catalog.json'
            self.assertEqual(main(['query','sql','SELECT target,kind FROM model_catalog ORDER BY target,kind','--limit','1000','--out',str(out)]),0)
            self.assertEqual(len(json.loads(out.read_text())['rows']),1000)
            self.assertNotIn('rows',json.loads(output.getvalue()))
            self.assertTrue(json.loads(output.getvalue())['truncated'])
