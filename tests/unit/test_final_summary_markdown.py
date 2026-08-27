from app.chat.markdown import FinalSummaryMarkdownStream


def test_stream_normalizes_heading_split_across_chunks() -> None:
    stream = FinalSummaryMarkdownStream()

    output = []
    output.extend(stream.feed("### Tóm tắt nhu"))
    output.extend(stream.feed(" cầu của bạn\nNội dung\n#### Nguồn dữ liệu"))
    output.extend(stream.feed(" và giới hạn\n"))
    output.append(stream.finish())

    assert "".join(output) == (
        "### Tóm tắt nhu cầu của bạn\n"
        "Nội dung\n"
        "### Nguồn và giới hạn dữ liệu\n"
    )


def test_stream_keeps_product_heading_and_links_unchanged() -> None:
    stream = FinalSummaryMarkdownStream()
    markdown = (
        "#### 1) Máy đo A\n"
        "![Máy đo A](https://cdn.example/a.jpg)\n"
        "[Xem tại Long Châu](https://nhathuoclongchau.com.vn/a)"
    )

    output = [*stream.feed(markdown), stream.finish()]

    assert "".join(output) == markdown


def test_stream_flushes_long_non_heading_fragments() -> None:
    stream = FinalSummaryMarkdownStream(flush_threshold=20)
    text = "Đây là một đoạn văn dài không có dấu xuống dòng nào cả"

    output = stream.feed(text)

    assert output == [text]


def test_stream_still_buffers_heading_fragments_for_normalization() -> None:
    stream = FinalSummaryMarkdownStream(flush_threshold=20)

    assert stream.feed("### Tóm tắt nhu cầu rất dài để vượt ngưỡng") == []

    output = stream.feed(" của bạn\n")

    assert "".join(output) == "### Tóm tắt nhu cầu của bạn\n"
