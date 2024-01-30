def extract_with_delimiters(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Define your own delimiters or markers
    code_block_delimiter = "\n<code>\n{}\n</code>\n"
    heading_delimiter = "\n<heading level={level}>\n{}\n</heading>\n"

    # Initialize the result text
    result_text = ""

    for element in soup.body.find_all(recursive=False):
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Handling headings
            level = element.name[1]  # Extract level number from tag name
            result_text += heading_delimiter.format(element.get_text(strip=True), level=level)
        elif element.name == 'pre' and element.code:
            # Handling code blocks
            result_text += code_block_delimiter.format(element.code.get_text(strip=True))
        else:
            # Handling other elements
            result_text += element.get_text(strip=True) + "\n"
    
    return result_text