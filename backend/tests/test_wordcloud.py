"""Word cloud endpoint tests - SCAFFOLD (test names = the behaviors to lock in).

These map 1:1 to functional requirements, so they double as the traceability
matrix for the SDD.
"""
# TODO(tests): implement against the conftest client fixture.

# def test_requires_title_or_industry(client):        # 422 when both missing
# def test_word_count_respected(client):              # len(words) <= word_count
# def test_shape_echoed(client):                      # response.shape == request.shape
# def test_unknown_role_404(client):
# def test_not_enough_data_422(client):               # role with no postings
# def test_weights_normalized(client):                # top word weight == 100
# def test_30_day_filter(client):                     # stale posting excluded (review#3)
# def test_keyword_extraction_no_false_positives():   # unit: keywords.extract_skills
