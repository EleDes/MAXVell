"""Retained UFM support codewords and explicitly diagnostic exact-input profiles."""
# SPDX-License-Identifier: 0BSD
import re


SUPPORT_FORMAT = "maxvell.ufm_source_sink_support.v1"
CANDIDATE_FORMAT = "maxvell.ufm_candidates.v1"
TARGET = "5M1270ZT144C5"
CFM_BITS = 208896


def _bit_offsets(value):
    if (not isinstance(value, list) or not value
            or any(type(x) is not int or not 0 <= x < CFM_BITS for x in value)
            or len(set(value)) != len(value)):
        raise ValueError("Invalid UFM support offset domain")
    return value


def _codewords(value, width, count):
    if (not isinstance(value, dict) or len(value) != count
            or any(not isinstance(k, str) or not k for k in value)
            or any(not isinstance(x, str) or len(x) != width
                   or set(x) - {"0", "1"} for x in value.values())
            or len(set(value.values())) != count):
        raise ValueError("Invalid UFM support codewords")
    return value


def offsets(provider):
    """Validate the admitted model and return its actual CFM section offsets."""
    if (not isinstance(provider, dict) or provider.get("target") != TARGET
            or type(provider.get("cfm_bits")) is not int
            or provider["cfm_bits"] != CFM_BITS
            or provider.get("bit_offset_domain") != "CFM_payload_lsb0"
            or provider.get("productive_emission_allowed") is not False
            or provider.get("canonical_functional_ir_allowed") is not False
            or not isinstance(provider.get("scope"), str) or not provider["scope"]):
        raise ValueError("Invalid UFM support model scope")
    if provider.get("format") == SUPPORT_FORMAT:
        source = _bit_offsets(provider.get("source_offsets"))
        sink = _bit_offsets(provider.get("sink_offsets"))
        sources = _codewords(provider.get("source_codewords"), 2, 2)
        sinks = _codewords(provider.get("sink_codewords"), 5, 4)
        if (len(source) != 2 or len(sink) != 5 or set(source) & set(sink)
                or set(sources) != {"dataout", "disconnected"}
                or any(re.fullmatch(r"LC_X\d+_Y\d+_N\d+", name) is None for name in sinks)
                or provider.get("canonical_support_ir_allowed") is not True
                or provider.get("complete_routes_proved") is not False
                or provider.get("event_behavior_proved") is not False):
            raise ValueError("Invalid source/four-sink support class")
        return set(source) | set(sink)
    if provider.get("format") != CANDIDATE_FORMAT:
        raise ValueError("Unsupported UFM support format")
    if any(provider.get(key) is not False for key in (
            "canonical_support_ir_allowed", "exact_input_scope_verified",
            "generic_selector_field_allowed", "coordinate_relative_generalization_allowed",
            "sink_connectivity_edge_allowed")):
        raise ValueError("UFM diagnostic profiles cannot grant input bindings")
    bindings = provider.get("input_bindings")
    profiles = provider.get("source_profiles")
    if (not isinstance(bindings, list) or len(bindings) != 11
            or not isinstance(profiles, list) or len(profiles) != 5
            or provider.get("input_binding_count") != 11
            or provider.get("input_offset_count") != 2837
            or provider.get("new_input_offset_count") != 2809
            or provider.get("source_profile_count") != 5):
        raise ValueError("UFM diagnostic profile population differs")
    result = set()
    input_ids = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError("Invalid UFM input fingerprint")
        selected = _bit_offsets(binding.get("bit_offsets"))
        word = binding.get("codeword")
        input_id = binding.get("input_id")
        pin = binding.get("source_pin")
        if (not isinstance(input_id, str) or input_id in input_ids
                or not isinstance(pin, str) or re.fullmatch(r"PIN_[A-Z0-9]+", pin) is None
                or not isinstance(word, str) or len(word) != len(selected)
                or set(word) - {"0", "1"} or result & set(selected)):
            raise ValueError("Invalid or overlapping UFM input fingerprint")
        input_ids.add(input_id)
        result.update(selected)
    if input_ids != {f"addr[{i}]" for i in range(9)} | {"nread", "oscena"} or len(result) != 2837:
        raise ValueError("UFM input fingerprint domain differs")
    profile_ids = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("Invalid UFM source profile")
        selected = _bit_offsets(profile.get("bit_offsets"))
        words = _codewords(profile.get("codewords_by_endpoint"), 3, 5)
        profile_id = profile.get("profile_id")
        if (len(selected) != 3 or not isinstance(profile_id, str) or not profile_id
                or profile_id in profile_ids
                or set(words) != {"disconnected", "dataout", "data_valid", "nbusy", "osc"}):
            raise ValueError("Invalid UFM semantic-source profile")
        profile_ids.add(profile_id)
        result.update(selected)
    return result


def _word(payload, selected):
    return "".join(str((payload[x // 8] >> (x % 8)) & 1) for x in selected)


def decode(provider, payload):
    """Match retained patterns; never infer UFM behavior or exact-input identity."""
    offsets(provider)
    if len(payload) * 8 != CFM_BITS:
        raise ValueError("UFM support CFM geometry differs")
    limits = {"target": TARGET, "scope": provider["scope"],
              "canonical_functional_ir_allowed": False, "productive_emission_allowed": False}
    if provider["format"] == SUPPORT_FORMAT:
        source_word = _word(payload, provider["source_offsets"])
        sink_word = _word(payload, provider["sink_offsets"])
        source = next((name for name, word in provider["source_codewords"].items()
                       if word == source_word), None)
        sink = next((name for name, word in provider["sink_codewords"].items()
                     if word == sink_word), None)
        edge = None
        if sink is None:
            status = "unmatched_sink_codeword"
        elif source is None:
            status = "unmatched_source_codeword"
        elif source == "disconnected":
            status = "decoded_disconnected_no_edge"
        else:
            status = "decoded_support_edge"
            edge = {"kind": "ufm_connectivity_support", "source": "UFM_X1_Y1_N4",
                    "source_port": "dataout[0]", "sink_lc": sink, "sink_port": "dataa",
                    "support_only": True, "productive_emission_allowed": False}
        return {**limits, "format": "maxvell.ufm_source_sink_support_ir.v1", "status": status,
                "source_codeword": source_word, "source_endpoint": source,
                "sink_codeword": sink_word, "sink_lc": sink, "edge": edge,
                "canonical_support_ir_allowed": True, "complete_routes_proved": False,
                "event_behavior_proved": False}
    inputs = []
    for binding in provider["input_bindings"]:
        observed = _word(payload, binding["bit_offsets"])
        inputs.append({"input_id": binding["input_id"], "candidate_pin": binding["source_pin"],
                       "offset_count": len(binding["bit_offsets"]),
                       "pattern_matches": observed == binding["codeword"]})
    profiles = []
    for profile in provider["source_profiles"]:
        observed = _word(payload, profile["bit_offsets"])
        endpoint = next((name for name, word in profile["codewords_by_endpoint"].items()
                         if word == observed), None)
        profiles.append({"profile_id": profile["profile_id"], "observed_codeword": observed,
                         "candidate_endpoint": endpoint, "pattern_matches": endpoint is not None})
    return {**limits, "format": "maxvell.ufm_candidates_ir.v1", "input_candidates": inputs,
            "source_candidates": profiles, "matched_input_patterns": sum(x["pattern_matches"] for x in inputs),
            "matched_source_profiles": sum(x["pattern_matches"] for x in profiles),
            "exact_input_scope_verified": False, "canonical_support_ir_allowed": False,
            "generic_selector_field_allowed": False, "coordinate_relative_generalization_allowed": False,
            "logical_nets_created": 0, "bindings_created": 0, "edges_created": 0}
