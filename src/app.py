from flask import Flask, render_template, request, make_response, jsonify, session, redirect, url_for
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import (
    LAParams,
    LTContainer,
    LTTextLine,
)
import numpy as np
import re, os
import pprint

app = Flask(__name__)
app.secret_key = "3eresults"

UPLOAD_FOLDER = './uploads'

# 氏名
NAME_CD = (808.5, 800.544, 965, 826)

# 性格特性(PERSONALITY_TRAITS)
PT_LABEL_CD = (62.0, 657.976, 104.0, 733.995)
PT_DEFINITION_CD = (207.0, 658.408, 305.034, 732.71)
PT_SCORE_CD = (185.0, 657.01, 193.0, 728.97)

# コミュニケーション力(COMMUNICATION)
CM_LABEL_CD = (62.0, 448.976, 122.865, 514.995)
CM_DEFINITION_CD = (207.0, 449.40799999999996, 323.034, 513.71)
CM_SCORE_CD = (185.0, 448.01, 193.0, 509.96999999999997)

# ラインタイプの閾値
LINE_TYPE_THRESHOLD = 3

# ヒューマンタイプ情報
HUMAN_TYPE_INFO = {
    "self-starter": {
        "class": "self-starter",
        "type_name": "セルフスタータータイプ",
        "strong": [
            "自分の意思で判断し、自ら積極的に行動する姿勢を持つ",
            "新しいことに前向きに取り組むチャレンジ精神がある",
            "自分の考え方や意図を率直かつ明確に伝えることができる"
        ],
        "week": [
            "単独行動が多く自分勝手に映る傾向がある",
            "飽きっぽく色々なことに手を出しがちで、仕事を中途半端に残してしまうことが考えられる",
            "相手の状況や感情を感じ取ったり、要望や期待を受け入れることが苦手"
        ],
        "point": [
            "本人の主体性を活かしてトライ&エラーを通じての育成が効果的。まずはやらせてみる。",
            "周囲への配慮が欠けたり、相手の感情を軽視したり、周囲を置き去りにして単独で進めてしまう場合は指摘が必要。",
            "中途半端な仕事の進め方にならないように、指示をしたことはメモなどで明確にしておき、進捗状況を確認するようにする。"
        ]
    },
    "follower": {
        "class": "follower",
        "type_name": "フォロワータイプ",
        "strong": [
            "チームワークを重んじ周囲と協力しながら仕事を進める",
            "相手の状況や感情を感じ取ることができ、場に応じた対応をすることができる",
            "一度はじめたことは完遂させるために、諦めずコツコツと取り組むことができる"
        ],
        "week": [
            "主体性が乏しく、自らの意志で行動することが不得意",
            "自分の考えや意図を率直かつ明確に伝えることが不得意",
            "変化よりも現状維持を好み、新しいことや未知の状況に対して臆病になる傾向がある"
        ],
        "point": [
            "組織内での役割や職務を明確にし、周囲と協働しながら成果を上げるような状況をつくることが先決。",
            "適時、5W1Hによる具体的な指示をしながら、仕事を進めさせる必要がある。本人任せにしてしまうと仕事が止まる可能性がある。",
            "都度復唱をさせるなど、理解が曖昧なまま仕事を進めさせないようにする。また、結論から伝えるなどのコミュニケーション上の指導も必要。"
        ]
    },
    "specialist": {
        "class": "specialist",
        "type_name": "スペシャリストタイプ",
        "strong": [
            "自分の意思で判断し、自ら積極的に行動する姿勢を強く持つ",
            "新しいことに前向きに取り組むチャレンジ精神がある",
            "相手の状況や感情を感じ取ることができ、場に応じた対応をすることができる"
        ],
        "week": [
            "自分の考えや意図を率直かつ明確に伝えることが不得意",
            "報告や相談なく、自分の判断だけで物事を進めてしまうことが考えられる",
            "飽きっぽく色々なことに手を出しがちで、仕事を中途半端に残してしまうことが考えられる"
        ],
        "point": [
            "本人の主体性を活かしてトライ&エラーを通じての育成がずはやらせてみる。",
            "周囲の理解・共感を得るためにも、意思伝達力や論理的表現力を高める必要があり、結論・理由・根拠(背景)の順で伝えさせる指導が効果的。",
            "中途半端な仕事の進め方にならないように、指示をしたことはメモなどで明確にしておき、進捗状況を確認するようにする。"
        ]
    },
    "commentator": {
        "class": "commentator",
        "type_name": "コメンテータータイプ",
        "strong": [
            "チームワークを重んじ周囲と協力しながら仕事を進める",
            "一度はじめたことは完遂させるために、諦めずコツコツと取り組むことができる",
            "自分の考えや意図を率直かつ明確に伝えることができる"
        ],
        "week": [
            "主体性が乏しく、自らの意志で行動・発言することが不得意",
            "変化よりも現状維持を好み、新しいことや未知の状況に対して臆病になる傾向がある",
            "それらしい理由をつけて言い訳や言い逃れをしようとする傾向がある"
        ],
        "point": [
            "組織内での役割や職務を明確にし、周囲と協働しながら成果を上げるような状況をつくることが先決。",
            "主体性を補うために、すべきことを5W1Hで考えさせ たり、業務の進捗・改善点を定期的に報告させる機会を作る。",
            "「あれこれ言う前にまず行動」のスタンスで指導する。仮説ではなく、自分で行った事実から考えさせるようにする。"
        ]
    },
    "chameleon": {
        "class": "chameleon",
        "type_name": "カメレオンタイプ",
        "strong": [
            "いずれの項目も平均的なタイプで、周囲に合わせることができる",
            "対人関係において苦手意識が少なく色々なタイプの人と付き合うことができる",
            "大概のことをそつなくこなすことができる"
        ],
        "week": [
            "特徴が分かり辛く、掴みどころのない印象を与えがち",
            "自分自身でも自己理解(強み・弱み)がし難い",
            "中庸であるがために強みを伸ばすことや弱みを改善する等の成⻑行動に結びつき辛い傾向がある"
        ],
        "point": [
            "本人の成⻑を促すために、意図的に挑戦的な高い目標を立てさせることが効果的。",
            "定期的に業務の進捗状況を確認し、背中を押して行動を促進させることが有効。"
        ]
    },
    "none": {
        "class": "chameleon",
        "type_name": "カメレオンタイプ<br><small>※分類が難しい場合はカメレオンタイプとなります。</small>",
        "strong": [
            "いずれの項目も平均的なタイプで、周囲に合わせることができる",
            "対人関係において苦手意識が少なく色々なタイプの人と付き合うことができる",
            "大概のことをそつなくこなすことができる"
        ],
        "week": [
            "特徴が分かり辛く、掴みどころのない印象を与えがち",
            "自分自身でも自己理解(強み・弱み)がし難い",
            "中庸であるがために強みを伸ばすことや弱みを改善する等の成⻑行動に結びつき辛い傾向がある"
        ],
        "point": [
            "本人の成⻑を促すために、意図的に挑戦的な高い目標を立てさせることが効果的。",
            "定期的に業務の進捗状況を確認し、背中を押して行動を促進させることが有効。"
        ]
    }
}

def get_objs(layout, results):
    if not isinstance(layout, LTContainer):
        return
    for obj in layout:
        if isinstance(obj, LTTextLine):
            text = re.sub(r"\s", "", obj.get_text())
            bbox = obj.bbox
            if (not('%' in  text)):
                if check_categorize(bbox, NAME_CD):
                    results['name'] = text
                elif check_categorize(bbox, PT_LABEL_CD):
                    results['pt']['label'].append(text)
                elif check_categorize(bbox, PT_DEFINITION_CD):
                    results['pt']['define'].append(text)
                elif check_categorize(bbox, PT_SCORE_CD):
                    results['pt']['score'].append(int(text))
                elif check_categorize(bbox, CM_LABEL_CD):
                    results['cm']['label'].append(text)
                elif check_categorize(bbox, CM_DEFINITION_CD):
                    results['cm']['define'].append(text)
                elif check_categorize(bbox, CM_SCORE_CD):
                    results['cm']['score'].append(int(text))
        get_objs(obj, results)

def check_categorize(bbox, range_cd):
    return bbox[0] >= range_cd[0] and bbox[1] >= range_cd[1] and bbox[2] <= range_cd[2] and bbox[3] <= range_cd[3]


def human_type_classfication(results):
    pt_line_type = line_type_classification(results['pt']['score'])
    cm_line_type = line_type_classification(results['cm']['score'])
    if (pt_line_type == 'left' and cm_line_type == 'left'):
        human_type = 'self-starter'
    elif (pt_line_type == 'right' and cm_line_type == 'right'):
        human_type = 'follower'
    elif (pt_line_type == 'left' and cm_line_type == 'right'):
        human_type = 'specialist'
    elif (pt_line_type == 'right' and cm_line_type == 'left'):
        human_type = 'commentator'
    elif (pt_line_type == 'center' and cm_line_type == 'center'):
        human_type = 'chameleon'
    else:
        human_type = 'none'
    return human_type

def line_type_classification(scores):
    first = scores[0]
    last = scores[-1]
    avg =  np.mean(scores)
    if (first > avg and avg > last + LINE_TYPE_THRESHOLD):
        line_type = 'left'
    elif (first < avg and avg + LINE_TYPE_THRESHOLD < last):
        line_type = 'right'
    else:
        line_type = 'center'
    return line_type

@app.route('/')
def top():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    return render_template('top.html', title='3E TEST RESULTER', results=session['results'] if 'results' in session.keys() else [], error=session['error'] if 'error' in session.keys()  else '', files=files)

@app.route('/', methods=['POST'])
def upload():
    results = {}
    if 'uploadFile' not in request.files:
        print(jsonify({'result':'uploadFile is required.'}))
    file = request.files['uploadFile']
    fileName = file.filename
    if '' == fileName:
        print(jsonify({'result':'filenrame must not empty.'}))
    filePath = os.path.join(UPLOAD_FOLDER, fileName)
    file.save(filePath)
    try:
        exec_3e_result(fileName, filePath, results)
    except:
        session['results'] = None
        session['error'] = 'フォーマットが違います'
        os.remove(filePath)
    return redirect(url_for('top'))

@app.route('/select_pdf', methods=['POST'])
def select_pdf():
    results = {}
    fileName = request.form.get('member_selector')
    filePath = os.path.join(UPLOAD_FOLDER, fileName)
    exec_3e_result(fileName, filePath, results)
    return redirect(url_for('top'))

def exec_3e_result(fileName, filePath, results):
    with open(filePath, "rb") as f:
        parser = PDFParser(f)
        document = PDFDocument(parser)
        if not document.is_extractable:
            raise PDFTextExtractionNotAllowed
        # https://pdfminersix.readthedocs.io/en/latest/api/composable.html#
        laparams = LAParams(
            all_texts=True,
        )
        rsrcmgr = PDFResourceManager()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)
            layout = device.get_result()
            results = {
                "file_name": fileName,
                "name": {},
                "pt": {
                    "label": [],
                    "define": [],
                    "score": []
                },
                "cm": {
                    "label": [],
                    "define": [],
                    "score": []
                },
                "type": {}
            }
            get_objs(layout, results)
            results['type'] = HUMAN_TYPE_INFO[human_type_classfication(results)]
    session['results'] = results

if __name__ == '__main__':
  app.run()
