import pytest
from modelagree.metrics import agreement

CAT={'type':'categorical','labels':['a','b']}
ORD={'type':'ordinal','levels':['low','mid','high']}
MULTI={'type':'multi_label','labels':['a','b']}


def test_categorical_hand_computed():
    result=agreement([('a','a'),('a','b'),('b','b'),('b','b')], CAT, failed=1)
    metrics=result['metrics']
    assert metrics['exact_agreement']=={'value':.75,'numerator':3,'denominator':4}
    # Marginals (2,2), (1,3): expected 1/2; (3/4 - 1/2)/(1 - 1/2)=1/2.
    assert metrics['cohen_kappa']['value']==.5
    assert metrics['cohen_kappa']['denominator']==.5
    assert metrics['cohen_kappa']['sample_size']==4
    assert result['confusion_matrix']['counts']==[[1,1],[0,2]]
    assert result['confusion_matrix']['denominator']==4
    assert result['failure_as_wrong']['exact_agreement']=={'value':.6,'numerator':3,'denominator':5}


def test_ordinal_hand_computed():
    result=agreement([('low','high'),('mid','high'),('high','low'),('mid','mid')],ORD,1)
    metrics=result['metrics']
    assert metrics['exact_agreement']['value']==.25
    assert metrics['cohen_kappa']['value']==pytest.approx(-1/11)
    assert result['confusion_matrix']['counts']==[[0,0,1],[0,1,1],[1,0,0]]
    for key,count in [('predictions_above',2),('predictions_below',1),('differences_at_least_two',2)]:
        assert metrics[key]=={'value':count/4,'numerator':count,'denominator':4}
    assert result['failure_as_wrong']['exact_agreement']['value']==.2


def test_multilabel_hand_computed():
    result=agreement([(['a'],['a','b']),([],[]),(['b'],[])], MULTI, failed=1)
    m=result['metrics']
    assert m['exact_set_agreement']=={'value':1/3,'numerator':1,'denominator':3}
    assert m['partial_overlap']=={'value':1/3,'numerator':1,'denominator':3}
    assert m['mean_jaccard']=={'value':.5,'numerator':1.5,'denominator':3}
    assert m['micro_f1']=={'value':.5,'numerator':2,'denominator':4,'sample_size':3,
                           'true_positive':1,'false_positive':1,'false_negative':1}
    lower=result['failure_as_wrong']
    assert lower['exact_set_agreement']['value']==.25
    assert lower['partial_overlap']['value']==.25
    assert lower['mean_jaccard']['value']==.375
    assert lower['micro_f1']['value']==1/3
    assert lower['micro_f1']['denominator']==6 and lower['micro_f1']['sample_size']==4


def test_sets_are_order_independent():
    assert agreement([(['a','b'],['b','a'])],MULTI)['metrics']['exact_set_agreement']['value']==1


@pytest.mark.parametrize('spec',[CAT,ORD,MULTI])
def test_no_eligible_items(spec):
    result=agreement([],spec,failed=2)
    assert all(m['value'] is None for m in result['metrics'].values())
    assert all(m['value']==0 for m in result['failure_as_wrong'].values())


def test_undefined_kappa_and_empty_micro_f1():
    kappa=agreement([('a','a')],CAT)['metrics']['cohen_kappa']
    assert kappa['value'] is None and kappa['denominator']==0
    assert kappa['sample_size']==1
    m=agreement([([],[])],MULTI)['metrics']
    assert m['micro_f1']['value'] is None and m['micro_f1']['denominator']==0
    assert m['mean_jaccard']['value']==1 and m['partial_overlap']['value']==0
