import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as wms


class WmsRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = wms.app.test_client()
        self.original_state = wms.snapshot_data()
        wms.products = {'P001': {'name': '測試商品', 'barcode': '123', 'unit': '個', 'category': '其他'}}
        wms.locations = {'L001': {'desc': '測試儲位'}}
        wms.stocks = {('P001', 'L001'): 5}
        wms.transactions = []

    def tearDown(self):
        wms.products, wms.locations, wms.stocks, wms.transactions = self.original_state

    def test_invalid_movement_quantities_do_not_change_stock(self):
        for endpoint, field, value in (
            ('inbound_submit', 'quantity', '-2'),
            ('inbound_submit', 'quantity', '0'),
            ('outbound_submit', 'quantity', '-2'),
            ('outbound_submit', 'quantity', '0'),
            ('inbound_submit', 'quantity', 'invalid'),
            ('stocktaking_submit', 'actual_quantity', '-1'),
        ):
            with self.subTest(endpoint=endpoint, value=value):
                path = {
                    'inbound_submit': '/inbound/submit',
                    'outbound_submit': '/outbound/submit',
                    'stocktaking_submit': '/stocktaking/submit',
                }[endpoint]
                response = self.client.post(
                    path,
                    data={'product_id': 'P001', 'location_id': 'L001', field: value},
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(wms.stocks[('P001', 'L001')], 5)
                self.assertEqual(wms.transactions, [])

    def test_zero_stocktaking_quantity_is_valid(self):
        with patch.object(wms, 'save_data'):
            response = self.client.post('/stocktaking/submit', data={
                'product_id': 'P001', 'location_id': 'L001', 'actual_quantity': '0',
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(wms.stocks[('P001', 'L001')], 0)
        self.assertEqual(wms.transactions[0]['quantity'], -5)

    def test_positive_inbound_and_outbound_update_stock_and_history(self):
        with patch.object(wms, 'save_data'):
            inbound_response = self.client.post('/inbound/submit', data={
                'product_id': 'P001', 'location_id': 'L001', 'quantity': '3',
            })
            outbound_response = self.client.post('/outbound/submit', data={
                'product_id': 'P001', 'location_id': 'L001', 'quantity': '2',
            })
        self.assertEqual(inbound_response.status_code, 302)
        self.assertEqual(outbound_response.status_code, 302)
        self.assertEqual(wms.stocks[('P001', 'L001')], 6)
        self.assertEqual([item['type'] for item in wms.transactions], ['入庫', '出庫'])

    def test_save_data_writes_json_under_configured_data_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.multiple(
                wms,
                DATA_DIR=root,
                PRODUCTS_FILE=root / 'products.json',
                LOCATIONS_FILE=root / 'locations.json',
                STOCKS_FILE=root / 'stocks.json',
                TRANSACTIONS_FILE=root / 'transactions.json',
            ):
                wms.save_data()
            saved_stocks = (root / 'stocks.json').read_text(encoding='utf-8')
            self.assertIn('P001,L001', saved_stocks)
            self.assertEqual(len(list(root.glob('*.json'))), 4)
            self.assertEqual(list(root.glob('tmp*')), [])

    def test_low_stock_filter_excludes_zero_and_stock_above_ten(self):
        wms.stocks.update({('P001', 'L002'): 0, ('P001', 'L003'): 11})
        wms.locations.update({'L002': {'desc': '零庫存'}, 'L003': {'desc': '高庫存'}})
        response = self.client.get('/inventory?filter=low_stock')
        self.assertEqual(response.status_code, 200)
        self.assertIn('測試儲位'.encode('utf-8'), response.data)
        self.assertNotIn('零庫存 <small'.encode('utf-8'), response.data)
        self.assertNotIn('高庫存 <small'.encode('utf-8'), response.data)

    def test_corrupt_json_raises_without_replacing_current_state(self):
        original_products = wms.products
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            products_file = root / 'products.json'
            products_file.write_text('{broken', encoding='utf-8')
            with patch.multiple(
                wms,
                PRODUCTS_FILE=products_file,
                LOCATIONS_FILE=root / 'locations.json',
                STOCKS_FILE=root / 'stocks.json',
                TRANSACTIONS_FILE=root / 'transactions.json',
            ):
                with self.assertRaisesRegex(ValueError, 'products.json'):
                    wms.load_data()
            self.assertEqual(products_file.read_text(encoding='utf-8'), '{broken')
        self.assertIs(wms.products, original_products)

    def test_save_failure_rolls_back_memory_and_reports_error(self):
        previous_products = wms.products.copy()
        with patch.object(wms, 'save_data', side_effect=OSError('disk full')):
            response = self.client.post('/products/add', data={
                'name': '新增', 'barcode': '456', 'unit': '個', 'category': '其他',
            }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wms.products, previous_products)
        self.assertNotIn('P002', wms.products)
        self.assertIn('資料儲存失敗'.encode('utf-8'), response.data)

    def test_delete_routes_require_post(self):
        self.assertEqual(self.client.get('/products/delete/P001').status_code, 405)
        self.assertEqual(self.client.get('/locations/delete/L001').status_code, 405)


if __name__ == '__main__':
    unittest.main()
