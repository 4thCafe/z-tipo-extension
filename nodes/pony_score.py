"""Pony Diffusion系スコアタグ(score_9, score_8_up等)を <|pony_score|> タググループとして扱うためのパッチ。

KGen(tipo-kgen)は score_* タグを POSSIBLE_QUALITY_TAGS に含めており、
seperate_tags() は <|quality|> グループに分類する。ここでは quality から
score系タグを分離し、新カテゴリ "pony_score" として扱えるようにする。
"""

PONY_SCORE_TAGS = frozenset(
    [f"score_{i}" for i in range(1, 10)] + [f"score_{i}_up" for i in range(1, 10)]
)


def patch_kgen_tag_lists():
    """kgen.formatter.tag_lists に pony_score カテゴリを追加する。

    seperate_tags() は tag_lists を挿入順に走査して先勝ちで分類するため、
    score系タグを quality から除去してから新カテゴリを追加する必要がある。
    """
    import kgen.formatter as formatter

    formatter.tag_lists["quality"] = set(formatter.tag_lists["quality"]) - PONY_SCORE_TAGS
    formatter.tag_lists["pony_score"] = set(PONY_SCORE_TAGS)


def inject_pony_score(tag_map, org_tag_map):
    """pony_score タグを tag_map に補完する。

    kgen.executor.tipo.parse_tipo_request は認識しないカテゴリキーを
    黙って破棄するため、TIPO生成パイプラインを経由すると pony_score は
    失われる。ユーザー入力を分類した org_tag_map から取り出し、
    フォーマット直前の tag_map に再注入して復元する。
    """
    tag_map["pony_score"] = list(org_tag_map.get("pony_score", []))
    return tag_map
