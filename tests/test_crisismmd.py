import csv
import importlib.util
import json
from pathlib import Path

import pytest

SPEC=importlib.util.spec_from_file_location('prepare_crisismmd',Path(__file__).resolve().parents[1]/'scripts'/'prepare_crisismmd.py')
converter=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(converter)


def write_annotations(root,rows,name='invented_event.tsv'):
    directory=root/'annotations'; directory.mkdir(exist_ok=True)
    with (directory/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['tweet_id','image_id','text_info','image_info','image_damage','tweet_text','image_path'],delimiter='\t')
        writer.writeheader(); writer.writerows(rows)


def row(image_id='synthetic-1_0',**changes):
    return {'tweet_id':'synthetic-1','image_id':image_id,'text_info':'not_informative',
            'image_info':'informative','image_damage':'severe_damage',
            'tweet_text':'An invented caption\twith a tab\nand a new line.','image_path':'data_image/pixel.png',**changes}


@pytest.fixture
def crisis(tmp_path,tiny_image):
    root=tmp_path/'CrisisMMD_v2.0'; (root/'data_image').mkdir(parents=True)
    (root/'data_image'/'pixel.png').write_bytes(tiny_image.read_bytes())
    return root


def test_converter_two_tasks_and_unknowns(crisis,tmp_path):
    write_annotations(crisis,[row(),row('synthetic-2_0',image_info='dont_know_or_cant_judge',image_damage=''),
                             row('synthetic-3_0',image_info='not_informative',image_damage='Mild damage',image_path='pixel.png')])
    out=tmp_path/'items.jsonl'; summary=converter.prepare(crisis,out)
    items=[json.loads(line) for line in out.read_text().splitlines()]
    assert summary['items_written']==3 and summary['unknown_informativeness']==1
    assert summary['unknown_damage_severity']==1
    assert items[0]['labels']=={'informativeness':'informative','damage_severity':'severe_damage'}
    assert items[1]['labels']=={'informativeness':None,'damage_severity':None}
    assert items[2]['labels']['damage_severity']=='mild_damage'
    assert items[0]['text']==row()['tweet_text'] and Path(items[0]['image']).is_file()
    assert items[0]['metadata']['original_labels']['text_info']=='not_informative'


@pytest.mark.parametrize('policy,expected',[('image','informative'),('text','not_informative'),('agreed',None)])
def test_information_policy(crisis,tmp_path,policy,expected):
    write_annotations(crisis,[row()]); out=tmp_path/'items.jsonl'
    converter.prepare(crisis,out,policy)
    assert json.loads(out.read_text())['labels']['informativeness']==expected


def test_duplicate_and_conflicting_ids(crisis,tmp_path):
    write_annotations(crisis,[row(),row()]); out=tmp_path/'items.jsonl'
    assert converter.prepare(crisis,out)['duplicates']==1
    original=out.read_bytes()
    write_annotations(crisis,[row(),row(image_damage='mild_damage')])
    with pytest.raises(ValueError,match='Conflicting'): converter.prepare(crisis,out)
    assert out.read_bytes()==original


def test_missing_image_is_never_silently_dropped(crisis,tmp_path):
    write_annotations(crisis,[row(),row('missing',image_path='data_image/absent.png')]); out=tmp_path/'items.jsonl'
    with pytest.raises(FileNotFoundError): converter.prepare(crisis,out)
    assert not out.exists()
    counts=converter.prepare(crisis,out,skip_missing_images=True)
    assert counts['missing_images_skipped']==1 and counts['items_written']==1


def test_path_escape_and_bad_headers(crisis,tmp_path):
    write_annotations(crisis,[row(image_path='../outside.png')])
    with pytest.raises(ValueError,match='escapes'): converter.prepare(crisis,tmp_path/'out')
    (crisis/'annotations'/'invented_event.tsv').write_text('bad\theader\n')
    with pytest.raises(ValueError,match='columns'): converter.prepare(crisis,tmp_path/'out')


def test_converter_cli(crisis,tmp_path,capsys):
    write_annotations(crisis,[row()])
    assert converter.main([str(crisis),'--output',str(tmp_path/'out.jsonl')])==0
    assert json.loads(capsys.readouterr().out)['items_written']==1
    assert converter.main([str(tmp_path/'missing')])==1
