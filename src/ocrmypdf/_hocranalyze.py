import re


hocr_post_orient_page_threshold = 0.5


def _correction_to_rotation(correction: int):
    return (360 - correction) % 360


def hocr_post_orient_page(input_hocr: str, page_index: int, context, log):
    """
    Detects page orientation based on actual OCR (hOCR) output.
    If a different orientation is detected, a post_rotation value is set for the current page in the context.
    :param input_hocr: The path to the file that contains the hOCR information of the current page
    :param page_index: The zero-based index of the current page in the document
    :param context:
    :param log:
    :return:
    """
    global hocr_post_orient_page_threshold
    
    # pdfinfo = context.get_pdfinfo()
    existing_rotation = context.get_rotation(page_index)  # pdfinfo[pageno].rotation
    page_num = page_index + 1

    symbols_by_angle = {}
    symbols_total = 0

    input_file = None
    try:
        input_file = open(input_hocr, "r")
        angle_regex = re.compile(r'textangle (\d+);')
        word_regex = re.compile(r'(?<=>)([^<\s]+)(?=<)')
        symbol_regex = re.compile(r'(?![0-9_])\w')

        # Iterate the hocr file line by line and find all ocr lines,
        # then check if we have an actual line of text, extract angle
        # and count letters
        for line in input_file:
            if "<span class='ocr_line'" in line:
                angle = 0
                angle_match = angle_regex.findall(line)

                if len(angle_match) == 1:
                    angle = int(angle_match[0])
                elif len(angle_match) > 1:
                    log.warning("Found more than 1 textangle value in an hocr line. The hOCR file might be damaged.")

                words = word_regex.findall(line)

                symbol_count = 0
                for word in words:
                    # To get rid of clutter from documents with lots of hand writig, we just pick clean
                    # unicode letters, excluding underscore (sure thing) and digits (todo: debatable)
                    symbols = symbol_regex.findall(word)
                    if len(symbols):
                        # log.info("Found word %s", ("".join(symbols))) # Naive debug output
                        symbol_count += sum(map(lambda sym: len(sym), symbols))

                if symbol_count:  # Not strictly necessary, just to avoid tuples with potential value of 0
                    if angle not in symbols_by_angle:
                        symbols_by_angle[angle] = 0

                    symbols_by_angle[angle] += symbol_count
                    symbols_total += symbol_count

        if len(symbols_by_angle) > 0:
            prevalent_angle = sorted(symbols_by_angle.items(), reverse=True, key=lambda item: item[1])[0]
            ratio = prevalent_angle[1] / symbols_total
            # If the percentage of the most current angle exceeds the threshold, we should rotate
            if ratio > hocr_post_orient_page_threshold:
                rotation = max(0, min(360, prevalent_angle[0]))
                if rotation != existing_rotation:
                    log.info("%4d: existing page rotation is %d°, content based rotation detected %d° (p=%.02f), "
                             "will change orientation" %
                             (page_num, _correction_to_rotation(existing_rotation), _correction_to_rotation(rotation), ratio))
                    
                    context.set_post_rotation(page_index, rotation)

        else:
            log.info("%4d: page seems not to have any readable text" % page_num)

    finally:
        if input_file is not None:
            input_file.close()
