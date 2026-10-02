#!/usr/bin/env python3
"""Convert a local CrisisMMD v2.0 annotations/ + data_image/ tree; no networking."""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

INFO={'informative':'informative','not_informative':'not_informative'}
DAMAGE={'little_or_no_damage':'little_or_no_damage', 'little_or_none':'little_or_no_damage',
        'little_or_none_damage':'little_or_no_damage', 'mild_damage':'mild_damage',
        'severe_damage':'severe_damage'}
REQUIRED={'tweet_id','image_id','text_info','image_info','image_damage','tweet_text','image_path'}


def normalize(value):
    return re.sub(r'[\s-]+','_', (value or '').strip().lower())


def local_image(root, value):
    if not value or '://' in value:
        raise ValueError('Annotation image_path must name a local image')
    relative=Path(value.replace('\\','/'))
    candidates=[root/relative,root/'data_image'/relative]
    if relative.parts and relative.parts[0]==root.name:
        candidates.append(root/Path(*relative.parts[1:]))
    for candidate in candidates:
        path=candidate.resolve()
        if not path.is_relative_to(root):
            raise ValueError('Annotation image_path escapes the dataset directory')
        if path.is_file(): return path
    raise FileNotFoundError('An annotated image is missing from the local dataset')


def prepare(dataset_dir, output, informativeness_source='image', skip_missing_images=False):
    root=Path(dataset_dir).resolve()
    output=Path(output).resolve()
    if informativeness_source not in {'image','text','agreed'}:
        raise ValueError('informativeness_source must be image, text, or agreed')
    files=sorted((root/'annotations').glob('*.tsv'))
    if not files:
        raise ValueError('Expected CrisisMMD v2.0 annotations/*.tsv under the dataset directory')
    seen={}
    items=[]
    counts=Counter(rows=0,duplicates=0,missing_images_skipped=0,unknown_informativeness=0,unknown_damage_severity=0)
    for source in files:
        with source.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle,delimiter='\t')
            if not REQUIRED.issubset(reader.fieldnames or []):
                raise ValueError(f'{source.name}: missing required CrisisMMD v2.0 annotation columns')
            for row_number,row in enumerate(reader,2):
                counts['rows']+=1
                if None in row or any(row.get(k) is None for k in REQUIRED):
                    raise ValueError(f'{source.name}:{row_number}: malformed TSV row')
                image_id=row['image_id'].strip()
                if not image_id or not row['tweet_id'].strip():
                    raise ValueError(f'{source.name}:{row_number}: missing identity')
                text_info=INFO.get(normalize(row['text_info']))
                image_info=INFO.get(normalize(row['image_info']))
                info={'image':image_info,'text':text_info,
                      'agreed':image_info if image_info==text_info else None}[informativeness_source]
                severity=DAMAGE.get(normalize(row['image_damage']))
                try:
                    image=local_image(root,row['image_path'])
                except FileNotFoundError:
                    if not skip_missing_images: raise
                    counts['missing_images_skipped']+=1
                    continue
                item={'id':image_id,'text':row['tweet_text'],'image':str(image),
                      'labels':{'informativeness':info,'damage_severity':severity},
                      'metadata':{'tweet_id':row['tweet_id'],'event':source.stem,
                                  'annotation_file':str(source.relative_to(root)),'annotation_row':row_number,
                                  'informativeness_source':informativeness_source,
                                  'original_labels':{key:row[key] for key in ('text_info','image_info','image_damage')}}}
                # Exact repeated observations collapse; conflicting evidence must be fixed explicitly.
                identity=(item['text'],item['image'],item['labels'],item['metadata']['tweet_id'],item['metadata']['original_labels'])
                if image_id in seen:
                    if seen[image_id] != identity:
                        raise ValueError(f'Conflicting annotations for image id {image_id}')
                    counts['duplicates']+=1
                    continue
                seen[image_id]=identity
                counts['unknown_informativeness']+=info is None
                counts['unknown_damage_severity']+=severity is None
                items.append(item)
    if not items:
        raise ValueError('No usable local image items; no dataset was written')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(dir=output.parent,prefix='.tmp-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle:
            for item in items: handle.write(json.dumps(item,ensure_ascii=False)+'\n')
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary,output)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return {**counts,'items_written':len(items),'informativeness_source':informativeness_source,'output':str(output)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset_dir',type=Path,help='Locally extracted CrisisMMD_v2.0 directory')
    parser.add_argument('--output',type=Path,default=Path('data/crisismmd/items.jsonl'))
    parser.add_argument('--informativeness-source',choices=['image','text','agreed'],default='image',
                        help='Reference column/policy; default image, matching the supplied image-focused prompt')
    parser.add_argument('--skip-missing-images',action='store_true',help='Explicitly skip and count missing local images')
    args=parser.parse_args(argv)
    try:
        summary=prepare(args.dataset_dir,args.output,args.informativeness_source,args.skip_missing_images)
    except (ValueError,OSError,csv.Error) as exc:
        print(f'prepare_crisismmd: {exc}',file=sys.stderr)
        return 1
    print(json.dumps(summary,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
