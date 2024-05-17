from datetime import datetime,date
import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_process_analysis")
def http_process_analysis(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP Process Analysis processed a request.')

    data = req.get_body()
    results = []
    if not data:
        return func.HttpResponse(
             results = {"results":""},status_code=200,)
    
    if data:
        logging.info(f'data found.')
        data_decode = data.decode('utf-8')
        json_data = json.loads(data_decode)
        analyzeResult = ""
        if 'analyzeResult' in json_data:
            analyzeResult = json_data['analyzeResult']
        #get date analyzed
        if 'createdDateTime' in json_data:
            date_analyzed = {"dateAnalyzed":json_data['createdDateTime'].split('T')[0] } 
            results.append(date_analyzed)
        #----------------- get entire content
        if 'content' in analyzeResult:
            fullContent = analyzeResult['content']
        if fullContent is not None:
            item = None
            item = {"full_content": fullContent }
            results.append(item)
        #----------------- get figure_sections - to match images with elements
        figures_json = get_figures(analyzeResult)
        results.append({"figures":figures_json})
        #----------------- get tables
        tables = []
        tables = extract_tables(analyzeResult)

        #combine all of the tables and their data into one object
        json_table = []
        contents_concat = ''
        for i in tables:
            for j in i:
                item = {"heading":j['heading']['value'],"content":""}
                for k in j['content']:
                    contents_concat =contents_concat + k['value'] + '\n'
                item['content'] = contents_concat
                json_table.append(item)
                contents_concat = ''
                item = None
            

        #item = {"tables":tables} if len(tables) > 0 else {"tables":[] }
        results.append({"combined_table_data":json.dumps(json_table)})
        #----------------- get selection marks
        selection_marks = get_selection_markes(analyzeResult=analyzeResult)
        results.append({"selectionMarks":selection_marks})
            
        #----------------- get paragraphs
        paragraphs = analyzeResult['paragraphs'] if 'paragraphs' in analyzeResult else None
        #----------------- filter and group headings and content paragraphs - remove the items that exist in the tables
        section = []
        cellLocations = []

        if paragraphs is not None:
            if cellLocations is None or len(cellLocations) <= 0:
                cellLocations = None
                cellLocations = []

            #----------------- get pagenumbers and offsets of table data
            cellLocations = get_table_cell_locations(tables)

            #filter the paragraphs
            filteredParagraphs = get_filtered_paragraphs(paragraphs,cellLocations)
            #group the sections
            selected_paragraph_items = select_from_paragraphs(filteredParagraphs)
            grouped_sections = groupSections(selected_paragraph_items)
            #TODO: Update to include value for selection marks using offset and pageNumber
            sections = {"sections":grouped_sections}
            results.append(sections)

        finalResult = {"contentResults":results}
        #results.append(sections)
        return func.HttpResponse(json.dumps(finalResult),status_code=200)
    else:
        return func.HttpResponse("Object analyzeResult was missing from the body.",status_code=500)  
    
#functions
def get_selection_markes(analyzeResult:json):
    selection_marks = []
    index = 0
    if 'pages' in analyzeResult and len(analyzeResult['pages']) > 0:
        for page in analyzeResult['pages']:
            if 'selectionMarks' in page and len(page['selectionMarks']) > 0:
                for mark in page['selectionMarks']:
                    item = None
                    item = {"state": mark['state'],"offset":mark['span']['offset'],"pageNumber":page['pageNumber']}
                    selection_marks.append(item)
    return selection_marks

def get_figures(analyzeResult: json):
    figures_json = []
    index = 0
    if 'figures' in analyzeResult and len(analyzeResult['figures'])>0:
        for figure in analyzeResult['figures']:
            item = None
            #----------------- take the index of the figure from the split element
            # if 'elements' in figure:
            #     for s in figure['elements']:            
            #         element_index =int(s.split('/')[2])
            #         item = {"element":s,"index":index,"page":figure['boundingRegions'][0]['pageNumber'],"offset":figure['spans'][0]['offset'],"length":figure['spans'][0]['length']}
            #         figures_json.append(item)
            #         index += 1
            # else:
            item = {"index":index,"page":figure['boundingRegions'][0]['pageNumber'],"offset":figure['spans'][0]['offset'],"length":figure['spans'][0]['length']}
            figures_json.append(item)
            index += 1

    return figures_json

def select_from_paragraphs(paragraphs: json):
    #select from paragraphs
    selected_paragraphs = []
    for paragraph in paragraphs:
        current_paragraph = None
        if 'role' in paragraph:

            current_paragraph = {paragraph['role'] : paragraph['content'],
                                 "pageNumber":paragraph['boundingRegions'][0]['pageNumber'],
                                 "offset":paragraph['spans'][0]['offset']}
            #json.loads(str(paragraph['role']) + ":" + str(paragraph['content']))
            selected_paragraphs.append(current_paragraph)
            current_paragraph = None
        else:
            if ':selected:' in paragraph['content'] or ':unselected:' in paragraph['content']:
                #split the string
                p_split = paragraph['content'].split(':')
                heading = p_split[0].strip()
                current_paragraph = {"selectionHeading":heading,
                                     "pageNumber":paragraph['boundingRegions'][0]['pageNumber'],
                                    "offset":paragraph['spans'][0]['offset'],"sectionContent":[]}

                for i in range(len(p_split)):
                    if p_split[i] == 'selected' or p_split[i] =='unselected':
                        #append the next index
                        current_paragraph['sectionContent'].append({p_split[i].strip():p_split[i+1].strip()})
                   
                # p_split = paragraph['content'].split(':selected:')
                # selected =p_split[1].strip()
                # p_split = paragraph['content'].split(':unselected:')
                # unselected = p_split[1].strip()
                # current_paragraph = {"SelectionHeading":heading,
                #                      "sectionContent":[{"Selected":selected},
                #                      {"pageNumber":paragraph['boundingRegions'][0]['pageNumber']},
                #                     {"offset":paragraph['spans'][0]['offset']},
                #                                        {"Unselected":unselected}]}
                selected_paragraphs.append(current_paragraph)
                current_paragraph = None
            else: 
                current_paragraph= {"sectionContent" : paragraph['content'],
                                    "pageNumber":paragraph['boundingRegions'][0]['pageNumber'],
                                    "offset":paragraph['spans'][0]['offset']}
                selected_paragraphs.append(current_paragraph)
                current_paragraph = None

    return selected_paragraphs

def get_filtered_paragraphs(paragraphs: json,table_cell_locations: list):
    filter_paragraphs = []
    #check table_cell_locations

    for i in range(0,len(paragraphs)):
        found = False
        keyvalue = str(paragraphs[i]['boundingRegions'][0]['pageNumber']) + str(paragraphs[i]['spans'][0]['offset'])
        for s in table_cell_locations:
            s_keyvalue = str(s['pageNumber']) + str(s['offset']) 
            if s_keyvalue == keyvalue:
                found = True
        if not found and paragraphs[i] is not None:
            filter_paragraphs.append(paragraphs[i])  
                

    return filter_paragraphs

def extract_tables(json_data: json):
    result = []
    if 'tables' in json_data and len(json_data['tables']) > 0:
        current_table = []
        headers = []
        contents = []
        for table in json_data['tables']:    
            table_kind = None
            #set the kind
            table_kind = table['cells'][0]['kind'] if len(table['cells'])>0 and 'kind' in table['cells'][0] else 'rowHeader'
            
            if table_kind is not None:
                if table_kind == 'columnHeader':
                    current_row = None
                    for cell in table['cells']:
                        if cell['rowIndex'] == 0:
                            #is header row
                            header = {"value":cell['content'],
                                       "pageNumber":cell['boundingRegions'][0]['pageNumber'],
                                       "offset":cell['spans'][0]['offset'], 
                                       "columnIndex":cell['columnIndex'],
                                       "rowIndex":cell['rowIndex'],
                                       "elements":cell['elements']} 
                            headers.append(header)
                        if cell['rowIndex'] > 0 and len(cell['content'])>0:
                            #is content row
                            content = {"value":cell['content'],
                                       "pageNumber":cell['boundingRegions'][0]['pageNumber'],
                                       "offset":cell['spans'][0]['offset'],
                                       "columnIndex":cell['columnIndex'],
                                       "rowIndex":cell['rowIndex'],
                                       "elements":cell['elements']} 
                            contents.append(content)
                    #for each header, get corresponding content
                    for i in range(0,len(headers)):
                        #append all row content to table and set to none
                        if current_row is not None and 'heading' in current_row:
                            current_table.append(current_row)
                            current_row = None
                        current_row = {"heading":headers[i],"content":[]}
                        for j in range(0,len(contents)):
                            if int(contents[j]['columnIndex'])==i:
                                current_row['content'].append(contents[j])
                    current_row = None

                        
                    #append the current table to the result array  
                    result.append(current_table)
                else:
                    #not columnHeader table - must be rowHeader
                    #TODO: Add code for row header tables
                    current_row = None
                    for cell in table['cells']:
                        if cell['columnIndex'] == 0:
                            #is header column
                            header = {"value":cell['content'],
                                       "pageNumber":cell['boundingRegions'][0]['pageNumber'],
                                       "offset":cell['spans'][0]['offset'], 
                                       "columnIndex":cell['columnIndex'],
                                       "rowIndex":cell['rowIndex'],
                                       "elements":cell['elements']} 
                            headers.append(header)
                        if cell['columnIndex'] > 0 and len(cell['content'])>0:
                            #is content row
                            content = {"value":cell['content'],
                                       "pageNumber":cell['boundingRegions'][0]['pageNumber'],
                                       "offset":cell['spans'][0]['offset'],
                                       "columnIndex":cell['columnIndex'],
                                       "rowIndex":cell['rowIndex'],
                                       "elements":cell['elements']} 
                            contents.append(content)
                    #for each header, get corresponding content
                    for i in range(0,len(headers)):
                        #append all row content to table and set to none
                        if current_row is not None and 'heading' in current_row:
                            current_table.append(current_row)
                            current_row = None
                        current_row = {"heading":headers[i],"content":[]}
                        for j in range(0,len(contents)):
                            if int(contents[j]['columnIndex'])==i:
                                current_row['content'].append(contents[j])
                    current_row = None

                        
                    #append the current table to the result array  
                    result.append(current_table)  
                    continue
           
    return result

def get_table_cell_locations(tables: json):
    cellLocations = []
    if tables is not None and len(tables)>0:
        for i in range(0,len(tables)):
            for table in tables[i]:
                    if 'heading' in table:
                            cellLocations.append({"pageNumber": table['heading']['pageNumber'], 
                                                        "offset": table['heading']['offset']})
                    if 'content' in table and len(table['content'])>0:
                        for item in table['content']:
                            cellLocations.append({"pageNumber": item['pageNumber'], 
                                                "offset": item['offset']})
    return cellLocations

def groupSections(json_data: dict):
    logging.info(f'Grouping Items for dataset')
    #logging.info(f'converting to utf-8 then json dump')
    
    results = []
    current_title = None
    current_section_heading = None
    current_page = 0
    try:
        for item in json_data:
            logging.info(f'current item: {item}')
            # Get page number
            if 'pageNumber' in item:
                current_page = item['pageNumber']
            else:
                current_page = '0'
            
            # Page Header
            if 'pageHeader' in item:
                if 'current_section_content' in locals() and not current_section_content:
                    results.append(current_section_content)
                    current_section_content = None
                current_section_heading = None
                current_section_content = {"pageHeader": item['pageHeader'], "pageNumber": current_page, "elements": item['elements'] if 'elements' in item else []}
                results.append(current_section_content)
                current_section_content = None

            # Page Footer
            elif 'pageFooter' in item:
                if 'current_section_content' in locals() and current_section_content:
                    results.append(current_section_content)
                    current_section_content = None
                current_section_heading = None
                current_section_content = {"pageFooter": item['pageFooter'], "pageNumber": current_page}
                results.append(current_section_content)
                current_section_content = None

            # Page Title
            elif 'title' in item:
                current_title = item['title']
                if 'current_section_content' in locals() and current_section_content:
                    results.append(current_section_content)
                    current_section_content = None
                
                current_section_heading = None
                current_section_content = {"title": current_title, "pageNumber": current_page}
                results.append(current_section_content)
                current_section_content = None

            elif 'sectionHeading' in item:
                if 'current_section_content' in locals() and current_section_content:
                    results.append(current_section_content)
                current_section_heading = item['sectionHeading']
                current_section_content = None
            
            elif 'selectionHeading' in item:
                if 'current_section_content' in locals() and current_section_content:
                    results.append(current_section_content)
                current_section_content = None
                current_section_heading = None
                current_section_heading = item['selectionHeading']
                current_section_content = {"sectionHeading":current_section_heading,"pageNumber":item['pageNumber'],
                                           "offset":item['offset'],
                                           "sectionContent":item['sectionContent']}
                results.append(current_section_content)
                current_section_content = None
                current_section_heading = None
                

            elif 'sectionContent' in item:
                logging.info(f'Checking if section content is associated with a heading.')
                if 'current_section_heading' in locals() and current_section_heading:
                    logging.info(f'section heading was found.')
                    if not 'current_section_content' in locals():
                        logging.info(f'current_section_content was not found in locals. Initializing now.')
                        current_section_content = {
                            "sectionHeading": current_section_heading,
                            "pageNumber": current_page,
                            "content": []
                        }
                    logging.info(f'Appending to current_section_content contents.')
                    if 'current_section_content' in locals() and current_section_content and 'content' in current_section_content:
                        current_section_content['content'].append(item['sectionContent'])
                    else:
                        logging.info(f'Creating current_section_content object for {item["sectionContent"]}')
                        current_section_content = {"sectionHeading":current_section_heading, "pageNumber": current_page, "content":[]}
                        current_section_content['content'].append(item['sectionContent'])
                else:
                    logging.info(f'Processing as standalone content - no heading found for content.')
                    current_section_content = {
                        "sectionHeading": None,
                        "pageNumber": current_page,
                        "content": [item['sectionContent']]
                    }
                    results.append(current_section_content)
            else:
                continue
        logging.info(f'Apply last append of current_section_content')
        if current_section_content:
            results.append(current_section_content)

        return results
    
    except UnboundLocalError as e:
        logging.error(f'An exception was encountered: Message: {repr(e)}')
        return func.HttpResponse(
             f'An exception was encountered: Message: {repr(e)}',
             status_code=500
        )
    except Exception as e:
        logging.error(f'An exception was encountered: Message: {repr(e)}')
        return func.HttpResponse(
             f'An exception was encountered: Message: {repr(e)}',
             status_code=500
        )