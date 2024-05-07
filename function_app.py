import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_process_analysis")
def http_process_analysis(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP Process Analysis processed a request.')

    data = req.get_body()
    #data = b'{"data":[{"title":"Q2 Marketing Plan for Jimmy John\'s (2024)"},{"sectionHeading":"Brief Summary"},{"sectionContent":"Brand"},{"sectionContent":"Jimmy John\'s"},{"sectionContent":"Brief Date"},{"sectionContent":"April 5, 2024"},{"sectionContent":"Brief Status"},{"sectionContent":"In Progress"},{"sectionContent":"Brand Team: Decision Maker"},{"sectionContent":"Dan Larkin"},{"sectionContent":"Brand Team: Point Person"},{"sectionContent":"Tom Evans"},{"sectionContent":"Brand Team: Inspire and IME"},{"sectionContent":"Jake Roder and EY Kalman"},{"sectionContent":"Briefing Output"},{"sectionContent":"Nationwide campaign for new sandwich line"},{"sectionContent":"Deliverable Date"},{"sectionContent":"October 10, 2024"},{"sectionHeading":"Business Overview"},{"sectionContent":"Jimmy John\'s is a popular sandwich chain known for its emphasis on fresh ingredients and speedy delivery. The brand prides itself on providing a high-quality, quick-service dining experience."},{"sectionHeading":"Objectives"},{"sectionContent":"The objective is to launch a new line of gourmet sandwiches that cater to evolving consumer tastes, with the goal of increasing same-store sales by 12% and online orders by 20%."},{"sectionHeading":"Opportunities To Achieve This [Growth]"},{"sectionContent":"Opportunities include leveraging social media for buzz around the new sandwich line, targeted email marketing campaigns, and promotional deals to incentivize trial."},{"sectionHeading":"Key Audiences"},{"sectionContent":"Our key audiences are busy professionals, college students, and health-conscious consumers looking for quick, nutritious meal options."},{"sectionHeading":"Additional Audience Context"},{"sectionContent":"Our audience values the convenience and reliability of Jimmy John\'s, and is open to trying new flavors and menu items that align with a health-conscious lifestyle."},{"sectionHeading":"Brand Context (Expert Perspective)"},{"sectionContent":"Industry experts see Jimmy John\'s as a brand that consistently delivers on quality and speed, with potential for growth in the health and wellness segment."},{"sectionHeading":"The Role Of Communications"},{"sectionContent":"Communications will focus on the freshness and quality of ingredients, the convenience of our service, and the innovation behind our new sandwich line."},{"sectionHeading":"Communications Ecosystem"},{"sectionContent":"Our communications ecosystem includes digital advertising, influencer partnerships, in-store signage, and community engagement through local events."},{"sectionHeading":"Historical Context"},{"sectionContent":"Jimmy John\'s has a history of successful product launches and marketing campaigns that emphasize the brand\'s commitment to quality and speed."},{"sectionHeading":"Success Criteria / Performance"},{"sectionContent":"Success will be measured by the uptake of the new sandwich line, customer feedback, online engagement metrics, and overall sales performance."},{"sectionHeading":"Other Considerations That Should Be Taken Into Account"},{"sectionContent":"We must consider the current market trends in health-conscious dining, the competitive landscape, and the operational implications of introducing new menu items."},{"sectionHeading":"Budget Details"},{"sectionContent":"The marketing budget is set at $3.5 million, with a focus on digital marketing channels and in-store promotional activities."},{"sectionHeading":"Project Check List"},{"sectionContent":"\xc2\xb7 Develop the new sandwich line and finalize menu offerings"},{"sectionContent":"\xc2\xb7 Plan the digital marketing strategy"},{"sectionContent":"\xc2\xb7 Design in-store promotional materials"},{"sectionContent":"\xc2\xb7 Organize launch events at select locations"}]}'
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
    try:
        for item in json_data['data']:
            logging.info(f'current item: {item}')
            if 'title' in item:
                current_title = item['title']
                if 'current_section_content' in locals():
                    results.append(current_section_content)
                    current_section_content = None
                
                current_section_heading = None
                current_section_content = {"title": current_title}
                results.append(current_section_content)
                current_section_content = None
            elif 'sectionHeading' in item:
                if 'current_section_content' in locals() and current_section_content is not None:
                    results.append(current_section_content)
                current_section_heading = item['sectionHeading']
                current_section_content = None
            elif 'sectionContent' in item:
                logging.info(f'Item is section content.')
                logging.info(f'Checking if section content is associated with a heading.')
                if 'current_section_heading' in locals():
                    logging.info(f'section heading was found.')
                    if not 'current_section_content' in locals():
                        logging.info(f'current_section_content was not found in locals. Initializing now.')
                        current_section_content = {
                            "sectionHeading": current_section_heading,
                            "content": []
                        }
                    logging.info(f'Appending to current_section_content contents.')
                    if current_section_content is not None and 'content' in current_section_content:
                        current_section_content['content'].append(item['sectionContent'])
                    else:
                        logging.info(f'Creating current_section_content object for {item["sectionContent"]}')
                        current_section_content = {"sectionHeading":current_section_heading,"content":[]}
                        current_section_content['content'].append(item['sectionContent'])
                else:
                    logging.info(f'Processing as standalone content - no heading found for content.')
                    current_section_content = {
                        "sectionHeading": None,
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