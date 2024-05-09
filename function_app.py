import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_process_analysis")
def http_process_analysis(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP Process Analysis processed a request.')

    data = req.get_body()
    data = b'{"data":[{"pageNumber":1,"sectionContent":"LOREM IPSUM SLOGAN HERE"},{"pageNumber":1,"title":"Fabulous City Fee Schedule"},{"pageNumber":1,"title":"Residential Fee Information"},{"pageNumber":1,"sectionContent":"Objective"},{"pageNumber":1,"sectionContent":"To excel at selling products."},{"pageNumber":1,"sectionContent":"Goals"},{"pageNumber":1,"sectionContent":"For the year, to increase revenue by 150%."},{"pageNumber":1,"sectionContent":"Project Checklist:"},{"pageNumber":1,"sectionContent":"1. Have the work done on time."},{"pageNumber":1,"sectionContent":"2. Do a great job."},{"pageNumber":1,"sectionContent":"Select an option: :selected: Cash :unselected: Card"},{"pageNumber":1,"sectionContent":"You selected cash for your preferred return method"},{"pageNumber":1,"sectionContent":"Card"},{"pageNumber":1,"sectionHeading":"See Table below:"},{"pageNumber":1,"sectionContent":"This is content that is designed to test document intelligence results."},{"pageNumber":1,"sectionContent":"How will document intelligence handle this? I wonder. I will test it with this document . I even included an emoji icon. Wonder what will happen?"},{"pageNumber":1,"pageFooter":"Contact us at 1-555-555-5555"},{"pageNumber":2,"sectionContent":"LOREM IPSUM SLOGAN HERE"},{"pageNumber":2,"title":"Fabulous City Fee Schedule"},{"pageNumber":2,"sectionContent":"Below is a nice image"},{"pageNumber":2,"pageFooter":"Contact us at 1-555-555-5555"}]}'
    if not data:
        return func.HttpResponse('No data was retrieved from the body.')
    if data:
        logging.info(f'data found. {data}')
        result = groupSections(data)
        returnResult = json.dumps(result)
        logging.info(f'results: {returnResult}')
        return func.HttpResponse(returnResult,status_code=200)
    else:
        return func.HttpResponse(
             "No data was found to process.",
             status_code=200
        )
    
def groupSections(data):
    logging.info(f'Grouping Items for dataset: {data}')
    #logging.info(f'converting to utf-8 then json dump')
    data_decode = data.decode('utf-8')
    json_data = json.loads(data_decode)
    results = []
    current_title = None
    current_section_heading = None
    current_page = 0
    try:
        for item in json_data['data']:
            logging.info(f'current item: {item}')
            # Get page number
            if 'pageNumber' in item:
                current_page = item['pageNumber']
            else:
                current_page = 0
            
            # Page Header
            if 'pageHeader' in item:
                if 'current_section_content' in locals():
                    results.append(current_section_content)
                    current_section_content = None
                current_section_heading = None
                current_section_content = {"pageHeader": item['pageHeader'], "pageNumber": current_page}
                results.append(current_section_content)
                current_section_content = None

            # Page Footer
            elif 'pageFooter' in item:
                if 'current_section_content' in locals():
                    results.append(current_section_content)
                    current_section_content = None
                current_section_heading = None
                current_section_content = {"pageFooter": item['pageFooter'], "pageNumber": current_page}
                results.append(current_section_content)
                current_section_content = None

            # Page Title
            elif 'title' in item:
                current_title = item['title']
                if 'current_section_content' in locals() and current_section_content is not None:
                    results.append(current_section_content)
                    current_section_content = None
                
                current_section_heading = None
                current_section_content = {"title": current_title, "pageNumber": current_page}
                results.append(current_section_content)
                current_section_content = None

            elif 'sectionHeading' in item:
                if 'current_section_content' in locals() and current_section_content is not None:
                    results.append(current_section_content)
                current_section_heading = item['sectionHeading']
                current_section_content = None
                
            elif 'sectionContent' in item:
                logging.info(f'Checking if section content is associated with a heading.')
                if 'current_section_heading' in locals():
                    logging.info(f'section heading was found.')
                    if not 'current_section_content' in locals():
                        logging.info(f'current_section_content was not found in locals. Initializing now.')
                        current_section_content = {
                            "sectionHeading": current_section_heading,
                            "pageNumber": current_page,
                            "content": []
                        }
                    logging.info(f'Appending to current_section_content contents.')
                    if current_section_content is not None and 'content' in current_section_content:
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