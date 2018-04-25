import bs4 as bs
from urllib.request import urlopen
from gremlin_python.process.traversal import Cardinality
from gremlin_python.process.graph_traversal import GraphTraversalSource
import gremlin_interface
from enum_vertex_edge_labels import VertexEdgeLabels


def create_service_region_edges(table_header: list, service_row: list, graph_traversal: GraphTraversalSource):
    for item_num in range(1, len(service_row)):
        if service_row[item_num] == '\uf00c' or service_row[item_num] == '✓':
            # print('Trying to map AWS-Service:', service_row[0], 'to AWS-Region:', table_header[item_num],end='')
            # Fetch Vertex ID's and create Edge only if AWS_Region Exists
            aws_region_vertex_list = gremlin_interface.fetch_vertex_list(graph_traversal,
                                                                        VertexEdgeLabels.vertex_label_aws_region.value,
                                                                        {'descriptive_name': table_header[item_num]})
            if len(aws_region_vertex_list) == 1:
                print('Mapping AWS-Service:', service_row[0], 'to AWS-Region:', table_header[item_num])
                aws_region_vertex_id = aws_region_vertex_list[0]

                aws_service_vertex_id = gremlin_interface.fetch_vertex_list(graph_traversal,
                                                                       VertexEdgeLabels.vertex_label_aws_service.value,
                                                                       {'name': service_row[0]})[0]

                # Fetch Edge List
                edge_list = gremlin_interface.fetch_edge_list(graph_traversal,
                                                             aws_service_vertex_id,
                                                             aws_service_vertex_id,
                                                             VertexEdgeLabels.edge_label_awsRegion_to_awsService.value)

                # Add Edge From AWS-Region to AWS-Service if edge does not exist
                if len(edge_list) == 0 and aws_region_vertex_id != '':
                    gremlin_interface.add_edge(graph_traversal,
                                               aws_region_vertex_id,
                                               aws_service_vertex_id,
                                               VertexEdgeLabels.edge_label_awsRegion_to_awsService.value)
                # print('--> committed')
            else:
                # print('--> not-committed')
                continue


def create_aws_service_vertex(service_name, graph_traversal):
    # Fetch AWS-Service Vertex list
    vertex_list = gremlin_interface.fetch_vertex_list(graph_traversal,
                                                     VertexEdgeLabels.vertex_label_aws_service.value,
                                                     {'name': service_name})
    if len(vertex_list) == 0:
        aws_service_vertex_id = gremlin_interface.add_vertex(graph_traversal,
                                                             VertexEdgeLabels.vertex_label_aws_service.value)
        gremlin_interface.add_update_vertex_properties(graph_traversal,
                                                       aws_service_vertex_id,
                                                       {'name': service_name})


def create_aws_services_vertex_edges(header_row: list, current_row: list, graph_traversal: GraphTraversalSource):
    create_aws_service_vertex(current_row[0], graph_traversal)
    create_service_region_edges(header_row, current_row, graph_traversal)


def clean_header_row(header_item_row: list):
    for item in header_item_row:
        # remove * from names
        # remove whitespaces
        header_item_row[header_item_row.index(item)] = item.replace('*', '').strip()
    return header_item_row


def map_aws_service_regions(html_table, graph_traversal: GraphTraversalSource):
    row_counter = 1
    table_header = []
    for tr in html_table.find_all('tr'):
        td = tr.find_all('td')
        row = [i.text for i in td]
        if len(row) != 0:
            if row_counter == 1:
                table_header = clean_header_row(row)
            else:
                # service_rows.append(clean_header_row(row))
                row = clean_header_row(row)
                create_aws_services_vertex_edges(table_header, row, graph_traversal)
        row_counter += row_counter


def fetch_raw_data_from_regional_product_services_page():
    aws_regions_endpoints_url = 'https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/'
    print('Scraping', aws_regions_endpoints_url, 'to get raw html data for AWS Services and their Region Availability')
    service_table_block_list = []
    with urlopen(aws_regions_endpoints_url) as html_page:
        soup = bs.BeautifulSoup(html_page.read().decode('utf-8'), 'lxml')
        for service_table_block in soup.find_all('li', class_='content-item'):
            service_table_block_list.append(service_table_block)
            # print(li_element.find_all('table'))
    return service_table_block_list


def create_aws_service_region_mapping(graph_traversal: GraphTraversalSource):
    # Fetch Service-Region HTML Table from the regional-product-services page
    tables_blocks_in_page = fetch_raw_data_from_regional_product_services_page()

    for table_block in tables_blocks_in_page:
        # print(type(table_block.find_all('table')[0]))
        map_aws_service_regions(table_block.find_all('table')[0], graph_traversal)


def load_aws_services_to_neptune(graph_traversal: GraphTraversalSource):
    print("Start --- Loading AWS Services and mapping to AWS-Regions to Neptune")
    create_aws_service_region_mapping(graph_traversal)
    print("Completed --- Loading AWS Services and mapping to AWS-Regions to Neptune\n")