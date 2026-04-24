"""
Tests for the QSO log feature: ADIF parser, bulk ingest, dedup, batches, export.
"""
import os

os.environ['DATABASE_PATH'] = 'test_qso_log.db'

import database as db
from features import qso_log


SAMPLE_ADIF = """ADIF export from unit test
<adif_ver:5>3.1.4
<programid:4>test
<eoh>

<call:6>EA1ABC<band:3>20m<mode:2>CW<qso_date:8>20260101<time_on:4>1530<rst_sent:3>599<rst_rcvd:3>579<name:4>John<eor>

<call:6>DL2XYZ<band:3>20m<mode:2>CW<qso_date:8>20260101<time_on:4>1535<rst_sent:3>599<rst_rcvd:3>599<eor>

<call:5>G4ABC<band:3>40m<mode:3>SSB<qso_date:8>20260101<time_on:4>1600<rst_sent:2>59<rst_rcvd:2>58<freq:5>7.150<eor>

<call:6>IK1DEF<freq:6>14.074<mode:3>FT8<qso_date:8>20260101<time_on:4>1620<rst_sent:3>-10<rst_rcvd:3>-15<eor>

<CALL:5>F5ZZZ<BAND:3>40m<MODE:2>CW<QSO_DATE:8>20260101<TIME_ON:4>1700<eor>
"""


def run_tests():
    print("Starting QSO log tests...\n")

    print("1. Initializing database...")
    db.init_database()
    print("[OK] Database initialized\n")

    print("2. Creating test operator and award...")
    success, _ = db.create_operator("EA4TEST", "Test Operator", "Testpass123", is_admin=False)
    assert success, "Failed to create operator"
    success, _, award_id = db.create_award("TEST1", "Test award")
    assert success and award_id, "Failed to create award"
    print(f"[OK] Created award id={award_id}\n")

    print("3. Testing streaming ADIF parser...")
    records = list(qso_log.parse_adif_stream(SAMPLE_ADIF))
    assert len(records) == 5, f"Expected 5 records, got {len(records)}"
    assert records[0]['call'] == 'EA1ABC', f"First record call wrong: {records[0]}"
    assert records[0]['band'] == '20m'
    assert records[0]['mode'] == 'CW'
    assert records[0]['qso_date'] == '20260101'
    assert records[0]['time_on'] == '1530'
    assert records[0]['name'] == 'John'
    # Lowercased tags
    assert records[4]['call'] == 'F5ZZZ'
    print(f"[OK] Parsed {len(records)} ADIF records\n")

    print("4. Testing ingest of sample ADIF...")
    result = qso_log.ingest_adif_bytes(
        award_id=award_id,
        operator_callsign="EA4TEST",
        file_bytes=SAMPLE_ADIF.encode('utf-8'),
        filename="test1.adi",
    )
    assert result['parsed'] == 5, f"parsed != 5: {result}"
    assert result['inserted'] == 5, f"inserted != 5: {result}"
    assert result['duplicates'] == 0, f"duplicates != 0: {result}"
    assert result['errors'] == 0, f"errors != 0: {result}"
    assert result['batch_id'] > 0, f"batch_id missing: {result}"
    print(f"[OK] Ingest result: {result}\n")

    print("5. Testing deduplication on re-upload...")
    result2 = qso_log.ingest_adif_bytes(
        award_id=award_id,
        operator_callsign="EA4TEST",
        file_bytes=SAMPLE_ADIF.encode('utf-8'),
        filename="test1_again.adi",
    )
    assert result2['parsed'] == 5
    assert result2['inserted'] == 0, f"inserted should be 0: {result2}"
    assert result2['duplicates'] == 5, f"duplicates should be 5: {result2}"
    print(f"[OK] Re-upload result: {result2}\n")

    print("6. Testing freq -> band derivation...")
    # The IK1DEF record has freq=14.074 but no band tag - should map to 20m
    qsos = qso_log.get_qsos_page(award_id, operator_callsign="EA4TEST", limit=100)
    ik1_rows = [q for q in qsos if q['call'] == 'IK1DEF']
    assert len(ik1_rows) == 1
    assert ik1_rows[0]['band'] == '20m', f"Expected 20m from freq 14.074, got {ik1_rows[0]['band']}"
    assert ik1_rows[0]['mode'] == 'FT8'
    print("[OK] Frequency-to-band derivation works\n")

    print("7. Testing malformed / incomplete records are dropped...")
    bad_adif = b"""<adif_ver:5>3.1.4<eoh>
<call:6>BAD001<eor>
<band:3>20m<mode:2>CW<qso_date:8>20260102<time_on:4>1200<eor>
<call:6>BAD003<band:3>20m<mode:2>CW<eor>
<call:6>GOOD01<band:3>20m<mode:2>CW<qso_date:8>20260102<time_on:4>1201<eor>
"""
    bad_result = qso_log.ingest_adif_bytes(award_id, "EA4TEST", bad_adif, "bad.adi")
    assert bad_result['parsed'] == 4
    assert bad_result['inserted'] == 1, f"Only GOOD01 should insert: {bad_result}"
    assert bad_result['errors'] == 3, f"Three records should error: {bad_result}"
    print(f"[OK] Malformed records dropped: {bad_result}\n")

    print("8. Testing pagination & counts...")
    total = db.count_qsos(award_id=award_id, operator_callsign="EA4TEST")
    assert total == 6, f"Expected 6 total QSOs, got {total}"
    page1 = db.get_qsos_page(award_id, "EA4TEST", limit=3, offset=0)
    page2 = db.get_qsos_page(award_id, "EA4TEST", limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    # Pages must not overlap
    ids1 = {q['id'] for q in page1}
    ids2 = {q['id'] for q in page2}
    assert ids1.isdisjoint(ids2), "Pages overlap"
    print(f"[OK] Pagination: total={total}, page1={len(page1)}, page2={len(page2)}\n")

    print("9. Testing filter by band/mode...")
    cw_20m = db.get_qsos_page(
        award_id, "EA4TEST", limit=100, band="20m", mode="CW"
    )
    # EA1ABC + DL2XYZ from SAMPLE_ADIF + GOOD01 from the malformed test
    assert len(cw_20m) == 3, f"Expected 3 20m CW QSOs, got {len(cw_20m)}"
    ft8_count = db.count_qsos(award_id=award_id, operator_callsign="EA4TEST", mode="FT8")
    assert ft8_count == 1, f"Expected 1 FT8 QSO, got {ft8_count}"
    print("[OK] Band/mode filters work\n")

    print("10. Testing stats aggregation...")
    stats = db.get_qso_stats(award_id, operator_callsign="EA4TEST")
    assert stats['total'] == 6
    assert stats['unique_calls'] == 6
    # 4x 20m (EA1ABC, DL2XYZ, IK1DEF, GOOD01) + 2x 40m (G4ABC, F5ZZZ)
    assert stats['by_band']['20m'] == 4, f"by_band wrong: {stats['by_band']}"
    assert stats['by_band']['40m'] == 2, f"by_band wrong: {stats['by_band']}"
    # 4x CW (EA1ABC, DL2XYZ, F5ZZZ, GOOD01) + 1x SSB + 1x FT8
    assert stats['by_mode']['CW'] == 4, f"by_mode wrong: {stats['by_mode']}"
    print(f"[OK] Stats: total={stats['total']}, bands={stats['by_band']}\n")

    print("11. Testing upload batches listing...")
    batches = db.get_upload_batches(award_id, operator_callsign="EA4TEST")
    assert len(batches) == 3, f"Expected 3 batches, got {len(batches)}"
    # Newest first - the bad.adi upload should be first
    assert batches[0]['filename'] == 'bad.adi'
    assert batches[0]['errors'] == 3
    print(f"[OK] Batches: {[b['filename'] for b in batches]}\n")

    print("12. Testing batch undo...")
    first_batch_id = next(b['id'] for b in batches if b['filename'] == 'test1.adi')
    ok, removed = db.delete_batch(first_batch_id, operator_callsign="EA4TEST")
    assert ok
    assert removed == 5, f"Should have removed 5 QSOs, got {removed}"
    remaining = db.count_qsos(award_id=award_id, operator_callsign="EA4TEST")
    assert remaining == 1, f"Expected 1 QSO left (GOOD01), got {remaining}"
    print(f"[OK] Undo removed {removed} QSOs, {remaining} remaining\n")

    print("13. Testing batch undo authorization (wrong operator)...")
    # Re-upload so we have a batch to test
    qso_log.ingest_adif_bytes(award_id, "EA4TEST", SAMPLE_ADIF.encode('utf-8'), "auth_test.adi")
    batches = db.get_upload_batches(award_id, operator_callsign="EA4TEST")
    test_batch_id = batches[0]['id']
    ok, _ = db.delete_batch(test_batch_id, operator_callsign="EB5NOPE")
    assert not ok, "Should reject delete by wrong operator"
    # But admin (no operator check) succeeds
    ok, _ = db.delete_batch(test_batch_id, operator_callsign=None)
    assert ok
    print("[OK] Batch delete authorization works\n")

    print("14. Testing ADIF export roundtrip...")
    # Re-upload and export, then re-parse the export and verify we get
    # the same logical records back.
    qso_log.ingest_adif_bytes(award_id, "EA4TEST", SAMPLE_ADIF.encode('utf-8'), "roundtrip.adi")
    all_q = db.get_qsos_page(award_id, "EA4TEST", limit=100)
    adif_text = db.export_qsos_to_adif(all_q, station_callsign="TEST1")
    assert "<adif_ver:5>3.1.4" in adif_text
    assert "<eoh>" in adif_text
    assert "<eor>" in adif_text
    # Count records in exported text
    exported_count = adif_text.lower().count("<eor>")
    assert exported_count == len(all_q), f"Export count mismatch: {exported_count} vs {len(all_q)}"
    # Re-parse the exported text
    reparsed = list(qso_log.parse_adif_stream(adif_text))
    assert len(reparsed) == len(all_q), f"Roundtrip record count wrong: {len(reparsed)}"
    calls_orig = {q['call'] for q in all_q}
    calls_reparsed = {r.get('call', '').upper() for r in reparsed}
    assert calls_orig == calls_reparsed, f"Calls differ: {calls_orig} vs {calls_reparsed}"
    print(f"[OK] Export roundtrip: {len(reparsed)} QSOs\n")

    print("15. Testing async ingest via thread pool...")
    future = qso_log.ingest_adif_async(
        award_id=award_id,
        operator_callsign="EA4TEST",
        file_bytes=SAMPLE_ADIF.encode('utf-8'),
        filename="async.adi",
    )
    async_result = future.result(timeout=10)
    assert async_result['parsed'] == 5
    # All 5 will be duplicates of existing QSOs from the roundtrip test
    assert async_result['duplicates'] == 5
    print(f"[OK] Async ingest: {async_result}\n")

    print("16. Testing oversized file rejection...")
    huge = b"a" * (qso_log.MAX_ADIF_UPLOAD_BYTES + 1)
    raised = False
    try:
        qso_log.ingest_adif_bytes(award_id, "EA4TEST", huge, "huge.adi")
    except ValueError:
        raised = True
    assert raised, "Should have raised ValueError on oversized file"
    print("[OK] Oversized file correctly rejected\n")

    print("17. Testing admin-wide stats scope...")
    # Create a second operator and ingest some QSOs
    db.create_operator("EB5TWO", "Op Two", "Testpass123", is_admin=False)
    op2_adif = """<adif_ver:5>3.1.4<eoh>
<call:6>JA1XXX<band:3>15m<mode:2>CW<qso_date:8>20260103<time_on:4>0800<eor>
<call:6>VK2YYY<band:3>15m<mode:3>SSB<qso_date:8>20260103<time_on:4>0900<eor>
"""
    qso_log.ingest_adif_bytes(award_id, "EB5TWO", op2_adif.encode('utf-8'), "op2.adi")
    # Per-operator scope
    own_stats = db.get_qso_stats(award_id, operator_callsign="EA4TEST")
    all_stats = db.get_qso_stats(award_id, operator_callsign=None)
    assert all_stats['total'] >= own_stats['total'] + 2
    assert 'EB5TWO' in all_stats['by_operator']
    assert all_stats['by_operator']['EB5TWO'] == 2
    print(f"[OK] Admin stats: per-op total={own_stats['total']}, all total={all_stats['total']}\n")

    print("18. Testing SUBMODE preference for digital modes...")
    submode_adif = b"""<adif_ver:5>3.1.4<eoh>
<call:6>KA1SUB<band:3>20m<mode:4>DATA<submode:3>FT8<qso_date:8>20260104<time_on:4>1200<eor>
"""
    qso_log.ingest_adif_bytes(award_id, "EA4TEST", submode_adif, "submode.adi")
    rows = db.get_qsos_page(award_id, "EA4TEST", limit=200)
    sub_row = next((q for q in rows if q['call'] == 'KA1SUB'), None)
    assert sub_row is not None
    assert sub_row['mode'] == 'FT8', f"Expected submode FT8, got {sub_row['mode']}"
    print("[OK] SUBMODE handling works\n")

    print("19. Testing by-date aggregation query...")
    by_date = qso_log.get_qsos_by_date(award_id, operator_callsign="EA4TEST")
    assert len(by_date) > 0, "Expected at least 1 date bucket"
    # All our test QSOs span 2026-01-01, 2026-01-02, 2026-01-04
    dates = [r['date'] for r in by_date]
    assert '2026-01-01' in dates, f"Missing 2026-01-01 in {dates}"
    total_from_dates = sum(r['count'] for r in by_date)
    expected = db.count_qsos(award_id, operator_callsign="EA4TEST")
    assert total_from_dates == expected, f"Sum mismatch: {total_from_dates} vs {expected}"
    # Sorted ascending
    assert dates == sorted(dates), f"Not sorted ascending: {dates}"
    print(f"[OK] by_date: {len(by_date)} date buckets, total={total_from_dates}\n")

    print("20. Testing by-hour aggregation query...")
    by_hour = qso_log.get_qsos_by_hour(award_id, operator_callsign="EA4TEST")
    assert len(by_hour) > 0, "Expected at least 1 hour bucket"
    hours = [r['hour'] for r in by_hour]
    # SAMPLE_ADIF has time_on 15:30, 15:35, 16:00, 16:20, 17:00 -> hours 15, 16, 17
    assert 15 in hours, f"Missing hour 15 in {hours}"
    assert 16 in hours, f"Missing hour 16 in {hours}"
    total_from_hours = sum(r['count'] for r in by_hour)
    assert total_from_hours == expected, f"Hour sum mismatch: {total_from_hours} vs {expected}"
    print(f"[OK] by_hour: {len(by_hour)} hour buckets\n")

    print("21. Testing band-mode matrix aggregation...")
    matrix = qso_log.get_qsos_band_mode_matrix(award_id, operator_callsign="EA4TEST")
    assert len(matrix) > 0, "Expected at least 1 band/mode pair"
    # Check that 20m/CW is present (EA1ABC, DL2XYZ, GOOD01)
    bm_lookup = {(r['band'], r['mode']): r['count'] for r in matrix}
    assert ('20m', 'CW') in bm_lookup, f"Missing 20m/CW in matrix"
    assert bm_lookup[('20m', 'CW')] >= 2, f"Expected >= 2 for 20m/CW: {bm_lookup[('20m', 'CW')]}"
    total_from_matrix = sum(r['count'] for r in matrix)
    assert total_from_matrix == expected, f"Matrix sum mismatch: {total_from_matrix} vs {expected}"
    print(f"[OK] band-mode matrix: {len(matrix)} pairs\n")

    print("22. Testing chart creation functions (non-crash)...")
    try:
        # Import charts directly (not through ui package which pulls in streamlit)
        import importlib.util
        _spec = importlib.util.spec_from_file_location("charts", "ui/charts.py")
        _charts = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_charts)
        create_qso_timeline_chart = _charts.create_qso_timeline_chart
        create_qso_band_mode_heatmap = _charts.create_qso_band_mode_heatmap
        create_qso_hourly_chart = _charts.create_qso_hourly_chart
        create_qso_band_chart = _charts.create_qso_band_chart
        create_qso_mode_chart = _charts.create_qso_mode_chart
        create_qso_operator_chart = _charts.create_qso_operator_chart
        t_en = {'qso_chart_daily': 'Daily', 'qso_chart_cumulative': 'Cumulative'}
        stats = qso_log.get_qso_stats(award_id, operator_callsign="EA4TEST")
        fig1 = create_qso_timeline_chart(by_date, t_en)
        assert fig1 is not None, "Timeline chart should not be None"
        fig2 = create_qso_band_mode_heatmap(matrix, t_en)
        assert fig2 is not None, "Band-mode heatmap should not be None"
        fig3 = create_qso_hourly_chart(by_hour, t_en)
        assert fig3 is not None, "Hourly chart should not be None"
        fig4 = create_qso_band_chart(stats['by_band'], t_en)
        assert fig4 is not None, "Band chart should not be None"
        fig5 = create_qso_mode_chart(stats['by_mode'], t_en)
        assert fig5 is not None, "Mode chart should not be None"
        # Empty data should return None
        assert create_qso_timeline_chart([], t_en) is None
        assert create_qso_band_mode_heatmap([], t_en) is None
        assert create_qso_hourly_chart([], t_en) is None
        assert create_qso_band_chart({}, t_en) is None
        assert create_qso_mode_chart({}, t_en) is None
        assert create_qso_operator_chart({}, t_en) is None
        print("[OK] All chart functions produce valid Plotly figures\n")

        print("23. Testing operator chart (admin scope)...")
        all_stats = qso_log.get_qso_stats(award_id, operator_callsign=None)
        assert len(all_stats['by_operator']) >= 2, f"Expected >=2 operators: {all_stats['by_operator']}"
        fig_ops = create_qso_operator_chart(all_stats['by_operator'], t_en)
        assert fig_ops is not None, "Operator chart should not be None"
        print(f"[OK] Operator chart with {len(all_stats['by_operator'])} operators\n")
    except ImportError as e:
        print(f"[SKIP] Chart tests skipped (missing dependency: {e})\n")

    print("=" * 50)
    print("All QSO log tests passed successfully!")
    print("=" * 50)


def cleanup():
    """Remove test database and sidecar files."""
    for suffix in ('', '-wal', '-shm'):
        try:
            os.remove(f'test_qso_log.db{suffix}')
        except FileNotFoundError:
            pass
    print("\nTest database cleaned up.")


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        exit(1)
    finally:
        cleanup()
