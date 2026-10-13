"""Retained candidate classes must not acquire new-input functional grants."""
import copy
import unittest
from maxvell import models
from maxvell.research import decode


def set_bit(payload, offset, value):
    payload[offset//8] = (payload[offset//8] & ~(1 << (offset%8))) | (value << (offset%8))


class ResearchTest(unittest.TestCase):
    def provider(self, kind):
        return models.load('5M1270ZT144C5' if kind == 'route_group_candidates' else '5M240ZT100C5', kind)[0]

    def test_route_group_positive_negative_disagreement_and_domain(self):
        provider = self.provider('route_group_candidates')
        payload = bytearray(provider['cfm_bits']//8)
        result = decode('route_group_candidates', provider, bytes(payload))
        self.assertEqual(result['state'], 'candidate_present')
        self.assertFalse(result['input_scope_verified'])
        self.assertFalse(result['canonical_functional_ir_allowed'])
        for offset in provider['offsets']:
            set_bit(payload, offset, 1)
        self.assertEqual(decode('route_group_candidates', provider, bytes(payload))['state'], 'candidate_absent')
        set_bit(payload, provider['offsets'][0], 0)
        result = decode('route_group_candidates', provider, bytes(payload))
        self.assertEqual(result['state'], 'blocked_duplicated_bit_disagreement')
        self.assertIsNone(result['candidate_present'])
        bad = copy.deepcopy(provider); bad['offsets'] = [offset+96 for offset in provider['offsets']]
        with self.assertRaises(ValueError):
            decode('route_group_candidates', bad, bytes(payload))

    def test_selector_qualification_known_unresolved_and_invalid_codes(self):
        provider = self.provider('selector_qualification')
        payload = bytearray(provider['cfm_bits']//8)
        for _, _, terms in provider['fields']:
            for offset, baseline in terms:
                set_bit(payload, offset, baseline)
        rows = decode('selector_qualification', provider, bytes(payload))['selector_instances']
        self.assertTrue(all(row['selector_state'] == 'inactive' for row in rows))
        for class_key, expected in ((provider['controlled_classes'][0], 'validated_active_class'),
                                    (provider['unresolved_classes'][0], 'unresolved_legal_class')):
            index, position = class_key
            site, _, terms = next(row for row in provider['fields'] if row[1] == index)
            a, b, _ = next(code for code in provider['codes'][index] if code[2] == position)
            for offset, baseline in terms:
                set_bit(payload, offset, baseline)
            for ordinal in (a, b+6):
                offset, baseline = terms[ordinal]; set_bit(payload, offset, 1-baseline)
            row = next(row for row in decode('selector_qualification', provider, bytes(payload))['selector_instances']
                       if row['site'] == site and row['field_index'] == index)
            self.assertEqual(row['selector_state'], expected)
            self.assertEqual(row['selector_position'], position)
            self.assertEqual(row['source_binding_status'], 'unresolved')
            other = (a+1)%6; offset, baseline = terms[other]; set_bit(payload, offset, 1-baseline)
            row = next(row for row in decode('selector_qualification', provider, bytes(payload))['selector_instances']
                       if row['site'] == site and row['field_index'] == index)
            self.assertEqual(row['selector_state'], 'invalid_one_hot')
            self.assertIsNone(row['selector_position'])

    def test_selector_qualification_overlap_is_rejected(self):
        provider = copy.deepcopy(self.provider('selector_qualification'))
        provider['unresolved_classes'][0] = provider['controlled_classes'][0]
        with self.assertRaises(ValueError):
            decode('selector_qualification', provider, bytes(provider['cfm_bits']//8))

    def test_lut_contexts_keep_conflicting_views_unselected(self):
        provider = self.provider('lut_context_candidates')
        exact = dict(provider['exact_sites'])
        cell = next(row for row in provider['cells'] if row[0] in exact and row[2] != exact[row[0]])
        site, offsets, controlled, _, _ = cell
        ordinal = next(i for i in range(16) if controlled[i] != exact[site][i])
        payload = bytearray(provider['cfm_bits']//8); set_bit(payload, offsets[ordinal], 1)
        result = decode('lut_context_candidates', provider, bytes(payload))
        views = next(row['context_views'] for row in result['cells'] if row['quartus_lc'] == site)
        self.assertEqual([int(view['mask'], 16) for view in views], [1 << controlled[ordinal], 1 << exact[site][ordinal]])
        self.assertNotEqual(views[0]['mask'], views[1]['mask'])
        self.assertTrue(all(view['selection_status'] == 'available_not_selected' for view in views))
        self.assertEqual(result['selected_context_view_count'], 0)
        self.assertFalse(result['input_topology_verified'])
        self.assertEqual(result['logical_nets_created'], 0)

    def test_context_permutation_and_scope_widening_are_rejected(self):
        provider = self.provider('lut_context_candidates')
        for change in ('duplicate', 'grant'):
            bad = copy.deepcopy(provider)
            if change == 'duplicate':
                bad['cells'][0][2][1] = bad['cells'][0][2][0]
            else:
                bad['input_topology_verified'] = True
            with self.assertRaises(ValueError):
                decode('lut_context_candidates', bad, bytes(bad['cfm_bits']//8))


if __name__ == '__main__':
    unittest.main()
