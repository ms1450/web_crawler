import re
from bs4 import BeautifulSoup
import socket
import ssl
import csv
import io

depth = 4
filename = 'companies.csv'
debug = True
connection_timeout_time = 3.0
limit_links_per_domain = True
limit_value = 500


# Returns port number to be used on the url
def find_port(raw_url):
    if 'https' in raw_url:
        return 443
    else:
        return 80


# Returns True if domain is same as url domain
def check_if_in_domain(domain, raw_url):
    raw_url = str(raw_url)
    port = find_port(raw_url)
    if port == 443:
        url = raw_url[8:]
    else:
        url = raw_url[7:]
    if url.endswith('/'):
        url = url[:-1]
    if url.count('/') == 0:
        return url == domain
    else:
        url = url[:url.find('/')]
        return url == domain


# Cleans out links (removes '?','#',';' values)
def clean_links(raw_url):
    hostname, address, port = parse_url(raw_url)
    clean_link = raw_url[:raw_url.find('/') + 2] + hostname + address
    return clean_link


# Parses a raw url into hostname, address, and port
def parse_url(raw_url):
    port_number = find_port(raw_url)
    if port_number == 443:
        url = raw_url[8:]
    else:
        url = raw_url[7:]
    if url.endswith('/'):
        url = url[:-1]
    if url.count('/') == 0:
        return url, '/', port_number
    else:
        starting_address = url[url.find('/'):]
        if '?' in starting_address:
            starting_address = starting_address[:starting_address.find('?')]
        if ';' in starting_address:
            starting_address = starting_address[:starting_address.find(';')]
        if '#' in starting_address:
            starting_address = starting_address[:starting_address.find('#')]
        if starting_address.endswith('/'):
            starting_address = starting_address[:-1]
        starting_address = re.sub(r'\n', '', starting_address)
        starting_address = re.sub(r'\r', '', starting_address)
        url = url[:url.find('/')]
        return url, starting_address, port_number


# Takes in Website Address -> Gives out HTML Code for the Website
def get_html(url, connection_port, address):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if connection_port == 443:
        context = ssl.create_default_context()
        connection = context.wrap_socket(connection, server_hostname=url)
    connection.connect((url, connection_port))
    request_header = "GET " + address + " HTTP/1.1\r\n" \
                     "Host: " + url + "\r\n" \
                     "Accept: */*\r\n" \
                     "Accept-Language: en-US\r\n" \
                     "User-Agent: Mozilla/5.0(Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko\r\n" \
                     "Connection: close\r\n\r\n"
    connection.settimeout(connection_timeout_time)
    connection.sendall(request_header.encode())
    response = ''
    while True:
        try:
            recv = connection.recv(1024).decode()
        except UnicodeDecodeError:
            continue
        if not recv:
            break
        response += str(recv)
    if 'HTTP' not in response.split(' ')[0]:
        return ""
    response_code = response.split(' ')[1]
    if int(response_code) == 301:
        headers = response.split('\n')
        for header in headers:
            if 'Location:' in header:
                return "HTTP->HTTPS: " + header[10:]
    html_boolean = False
    if connection_port == 443:
        parsed_html = ""
        for line in response.split('\n'):
            if not line.find("<!--") or html_boolean:
                parsed_html += line + "\n"
                html_boolean = True
        return parsed_html
    else:
        parsed_html = ""
        for line in response.split('\n'):
            if not line.find("<HTML>") or html_boolean:
                parsed_html += line + "\n"
                html_boolean = True
        return parsed_html


# Takes in Website Address -> Give out depth of Link
def get_depth_from_link(depth_address):
    link_depth = str(depth_address).count('/')
    return link_depth


# Takes in HTML and returns all the links found within
def get_links_from_html(domain_name, port_number, html_page):
    links_found = set()
    if html_page == '':
        return links_found
    elif "HTTP->HTTPS: " in html_page and port_number == 80:
        if debug:
            print("-\tChanged Domain to Access HTTPS Page")
            print("-\t" + domain_name + " TO " + html_page[13:].strip().lower())
        links_found.add(clean_links(html_page[13:].strip().lower()))
        return links_found
    elif port_number == 80:
        links_in_page_set = re.findall('"((http)s?://.*?)"', html_page)
        for link_found_set in links_in_page_set:
            temporary_link = str(link_found_set[0])
            if check_if_in_domain(domain_name, temporary_link):
                links_found.add(clean_links(temporary_link))
        return links_found
    else:
        soup = BeautifulSoup(html_page, 'html.parser')
        all_links = [a.get('href') for a in soup.find_all('a', href=True)]
        for link_found in all_links:
            append = False
            if len(str(link_found)) <= 1:
                continue
            if check_if_in_domain(domain_name, link_found):
                append = True
            elif str(link_found)[:1] == '/':
                link_found = "https://" + domain_name + link_found
                append = True
            if append and link_found not in links_found and get_depth_from_link(link_found) <= depth + 2:
                if str(link_found)[-1:] == '/':
                    link_found = str(link_found)[:-1]
                if "mailto:" in str(link_found):
                    continue
                else:
                    links_found.add(clean_links(link_found))
        return links_found


# Takes in unformatted addresses and returns formatted addresses set
def format_given_addresses(link_addresses):
    # Used for Statistics
    total = len(link_addresses)
    count = 0
    # Stores the formatted addresses
    formatted_address_list = set()
    for link_addr in link_addresses:
        count += 1
        hostname, address, port = parse_url(link_addr)
        backslashes = str(address).count('/')
        # Case where address is /address
        if backslashes == 1:
            if address not in formatted_address_list:
                formatted_address_list.add(address)
        else:
            while backslashes != 1:
                sub_string = address[:address.find('/', 1)]
                if sub_string not in formatted_address_list:
                    formatted_address_list.add(sub_string)
                address = address[len(sub_string):]
                backslashes -= 1
                if address == '':
                    break
            if address not in formatted_address_list:
                formatted_address_list.add(address)
        if debug:
            print(str(count) + "/" + str(total))
    return formatted_address_list


# Takes in a Domain Link and returns formatted address list
def domain_crawler(domain_link):
    print("Crawling " + repr(domain_link))
    visited_links = set()
    links_to_search = set()
    links_to_search.add(domain_link)
    links_count = 0
    while len(links_to_search):
        if limit_links_per_domain and links_count > limit_value:
            break
        search_link = links_to_search.pop()
        hostname, address, port = parse_url(search_link)
        if debug:
            print("+\t" + hostname + address)
        if 'getattachment' in address:
            visited_links.add(search_link)
            continue
        try:
            links_gathered = get_links_from_html(hostname, port, get_html(hostname, port, address))
        except socket.gaierror:
            continue
        except socket.timeout or TimeoutError:
            if debug:
                print("-\tConnection with Server timed out")
            visited_links.add(search_link)
            continue
        except ConnectionResetError:
            if debug:
                print("-\tConnection with Server was reset")
                visited_links.add(search_link)
            continue
        except ssl.SSLCertVerificationError:
            if debug:
                print("-\tIncorrect SSL Certificate")
            continue
        except OSError:
            if debug:
                print("-\tNot a Valid Address")
            continue
        visited_links.add(search_link)
        links_count += 1
        for link_found in links_gathered:
            if link_found not in visited_links:
                links_to_search.add(link_found)
    print("Completed Crawling " + domain_link)
    formatted_link_addresses = format_given_addresses(visited_links)
    return formatted_link_addresses


# Reads from CSV file and returns a list with all the domain links
def read_from_csv():
    domain_links = []
    with open(filename, 'r') as domain_file:
        csv_file = csv.reader(domain_file)
        for lines in csv_file:
            domain_links.append(lines.pop())
    return domain_links


# writes provided links to file
def write_to_file(formatted):
    file = io.open('paths.list', "w", encoding="utf-8")
    for link_ in formatted:
        if link_ != "":
            file.write(link_ + "\n")
    file.close()


# Main Function
if __name__ == '__main__':
    domain_list = read_from_csv()
    all_formatted_links = set()
    for link in domain_list:
        try:
            formatted_links = domain_crawler(link)
        except KeyboardInterrupt:
            if debug:
                print("Keyboard Interrupt Caught")
            continue
        all_formatted_links.update(formatted_links)
    write_to_file(all_formatted_links)
    print("Completed.")
