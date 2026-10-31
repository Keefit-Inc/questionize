from questionize.source_input import source_input_issues


def test_lone_deictic_prompt_is_not_a_complete_argument():
    for text in ['Which claim strengthens the conclusion drawn in the passage?', 'The argument above depends on', "Mira’s argument relies on the assumption that"]:
        assert 'missing_referenced_stimulus' in source_input_issues({'passage':text,'stem':''})


def test_restored_passage_and_standalone_choices_are_not_rejected():
    assert not source_input_issues({'passage':'All devices in this set are blue. The token is in the set.','stem':'Which conclusion follows?'})
    assert not source_input_issues({'passage':'','stem':'Which of the following is a self-contradictory statement?'})
    assert not source_input_issues({'passage':'The premises imply a result because ____.','stem':''})


def test_photo_integrity_guard_rejects_missing_referenced_passage():
    from questionize.integrity import integrity_issues
    from questionize.schemas import SourceQuestion,Choice
    q=SourceQuestion(passage='',stem='Which choice weakens the argument above?',choices=[Choice(label=l,text='Choice '+l) for l in 'ABCDE'])
    assert 'missing_referenced_stimulus' in integrity_issues(q)
