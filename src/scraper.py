from bs4 import BeautifulSoup as soup
import selenium, time, os
import pandas as pd
import json
data_path = os.path.join('..','data')
if not os.path.exists(data_path):
    os.makedirs(data_path)

def get_html(url='https://www.bigbasket.com/pc/snacks-branded-foods/snacks-namkeen/', max_pages=60):
    """Gets complete html for a page be iteratively scrolling to the bottom.

    Args:
        url (str, optional): Page URL. Defaults to 'https://www.bigbasket.com/pc/snacks-branded-foods/snacks-namkeen/'.
        max_pages (int, optional): Maximum number of pages. Defaults to 60.

    Returns:
        str: Path of file containing page source as HTML
    """
    fpath = os.path.join(data_path,"%s.html"%url.split('/')[-2])
    if os.path.exists(fpath):
        return fpath

    chrome_options = selenium.webdriver.ChromeOptions()
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    browser = selenium.webdriver.Chrome(chrome_options=chrome_options)
    browser.get(url)
    time.sleep(3)

    print ('Jumping to page end')
    lenOfPage = browser.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    match = False
    while(match==False):
        lastCount = lenOfPage
        lenOfPage = browser.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        if lastCount==lenOfPage:
            match=True
    time.sleep(3)

    print ('Show more loop')
    while True:
        if int(browser.current_url.split('page=')[-1])>60:break
        try:browser.find_element_by_css_selector("button[ng-click='vm.pagginator.showmorepage()']").click();time.sleep(1.5)
        except selenium.common.exceptions.ElementNotInteractableException:break
    time.sleep(5)

    with open(fpath,'w') as html_file:
        html_file.write(browser.page_source)
    print("FPATH:%s"%fpath)
    return fpath

def _proc_mul_qty(qty_val):
    """Processes strings with multiple quantities joined by * or +

    Args:
        qty_val (str): Quantity String

    Returns:
        float: Quantity
    """
    try:
        qty_val = float(qty_val.split('x')[0])*float(qty_val.split('x')[1]) if 'x' in qty_val else float(qty_val)
    except:
        try:
            qty_val = float(qty_val.split('+')[0])+float(qty_val.split('+')[1]) if '+' in qty_val else float(qty_val)
        except:
            print ("FAILED :%s"%qty_val)
    return qty_val

def _multi_replace(string, rep_dict):
    """Replaces string with pairs in a dict.
    Alternatively, if rep_dict is a list, replaces list of words with ''

    Args:
        string (str): String to replace in
        rep_dict (dict): Dict of words to

    Returns:
        [type]: [description]
    """
    if isinstance(rep_dict, list):
        rep_dict = {rep_x:'' for rep_x in rep_dict}
    for word, rep_word in rep_dict.items():
        string = string.replace(word, rep_word)
    return string

def _strip_right(string, words):
    for word in words:
        word = word.strip().split(word)[0]
    return word

def get_all_prod_df(htm_path='/Users/vishalgupta/Downloads/Snacks_62.htm'):
    """Fetches all products in a category ie. category page.

    Args:
        htm_path (str, optional): Path of html source. Defaults to '/Users/vishalgupta/Downloads/Snacks_62.htm'.

    Returns:
        pandas.DataFrame: Datafrom with all products' names, brands, ratings, quantities and prices
    """
    with open(htm_path) as f:
        snacks_html = f.read()
    prods = soup(snacks_html).findAll('div',{'qa':"product"})
    all_prods = []
    for prod in prods:
        prod_name = prod.findAll('div',{'qa':"product_name"})[0]
        new_prod = {}
        new_prod['brand'] = prod_name.select_one('h6').text.strip()
        # print(new_prod, prod_name.text)
        try:new_prod['ratings'] = prod_name.findAll('span',{'ng-bind':"vm.selectedProduct.rating_info.rating_count"})[0].text
        except IndexError: new_prod['ratings'] = 0
        # print(new_prod)
        new_prod['name'] = prod_name.select_one('a').text.strip()
        # print(new_prod)
        new_prod['qtys'] = [i.text.strip() for i in prod.findAll('div',{'class':"qnty-selection"})[0].select('a')]
        if len(new_prod['qtys']) == 0:
            new_prod['qtys'] = [prod.findAll('div',{'class':"qnty-selection"})[0].text.strip()]
        print(new_prod)
        try:new_prod['price'] = prod.findAll('span',{'class':"mp-price"})[0].text
        except:new_prod['price'] = prod.findAll('div',{'qa':"price"})[0].text
        all_prods.append(new_prod)

    all_prod_rows = []
    rep_all = lambda x: _multi_replace(_strip_right(x,['g','pcs','ml']), ['combo', 'items', '(', ')', 'k', 'item', 'sheets', 'pouch'])
    for prod in all_prods:
        if len(prod['qtys'])>1:
            for qty in prod['qtys']:
                qty_val, price = qty.split('-')
                qty_val = rep_all(qty_val.lower().strip()).strip()
                price = float(price.strip().split('Rs ')[-1].strip())
                qty_val = proc_mul_qty(qty_val)
                all_prod_rows.append({'name':prod['name'], 'brand':prod['brand'], 'ratings':prod['ratings'], 'price':price, 'qty':qty_val})
        else:
            qty_val = rep_all(prod['qtys'][0].lower().strip()).strip()
            price = float(prod['price'].strip().split('Rs ')[-1].strip())
            qty_val = proc_mul_qty(qty_val)
            all_prod_rows.append({'name':prod['name'], 'brand':prod['brand'], 'ratings':prod['ratings'], 'price':price, 'qty':qty_val})

    all_prods_df = pd.DataFrame(all_prod_rows)
    return all_prods_df

def eda(all_prods_df):
    """Summarizes results from a products DataFrame.
    Change depending on application.

    Args:
        all_prods_df (pandas.DataFrame): Products DataFrame

    Returns:
        pandas.DataFrame: Results DataFrame
    """
    all_prods_df['qty_per_re'] = all_prods_df['qty']/all_prods_df['price']
    all_prods_df['ratings'] = all_prods_df['ratings'].astype(int)
    multi_qty_prods = all_prods_df['name'].value_counts()[all_prods_df['name'].value_counts()>1].index
    res_df = all_prods_df[(all_prods_df.name.isin(multi_qty_prods))].groupby(['name','brand','ratings']).apply(lambda temp_df : (temp_df.qty_per_re.iloc[temp_df.price.argmin()]/temp_df.qty_per_re.iloc[temp_df.price.argmax()]).round(4)*100).sort_values().reset_index()
    res_df = res_df[(res_df[0]>50)&(res_df[0]<300)]
    req_pattern_flags = res_df.groupby('brand').apply(lambda x:(x[0].nunique()>1) and (x['ratings'].mean()>100))
    res_pattern_brands = req_pattern_flags[req_pattern_flags].index
    res_df = res_df[res_df.brand.isin(res_pattern_brands)]
    return res_df

def get_link_tree():
    """Generates link tree with all categories and subcategories.

    Returns:
        dict: Link Tree
    """
    link_tree = {}
    chrome_options = selenium.webdriver.ChromeOptions()
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    browser = selenium.webdriver.Chrome(chrome_options=chrome_options)
    browser.maximize_window()
    browser.get('https://www.bigbasket.com/')
    time.sleep(2)
    s = soup(browser.page_source)
    cat_links = dict([(x.text,x.attrs['href']) for x in s.findAll('ul',{'class':"nav-tabs"})[0].select('a')])
    link_tree = {cat_name:{'root':'https://www.bigbasket.com'+link} for cat_name, link in cat_links.items()}
    for cat in link_tree:
        browser.get(link_tree[cat]['root'])
        time.sleep(2)
        sub_cat_links = dict([(i.select_one('a').text,'https://www.bigbasket.com'+i.select_one('a').attrs['href'].split('?nc')[0]) for i in soup(browser.page_source).findAll('div',{'class':'subcat'})])
        link_tree[cat].update(sub_cat_links)
    with open(os.path.join(data_path,'link_tree.json'),'w') as f:
        json.dump(link_tree)
    return link_tree

def explore_cat(cat_name = 'Snacks & Branded Foods'):
    """Walks over all links and pages in a Categories and aggregates results.

    Args:
        cat_name (str, optional): Category Name. Must be a valid category in the link tree. Defaults to 'Snacks & Branded Foods'.
    """
    if os.path.exists(os.path.join(data_path,'link_tree.json')):
        with open(os.path.join(data_path,'link_tree.json'),'r') as f:
            link_tree = json.load(f)
    else:
        link_tree = get_link_tree()
    all_res_df = pd.DataFrame()
    for subcat in link_tree[cat_name]:
        if subcat == 'root':continue
        print (link_tree[cat_name][subcat])
        source_path = get_html(url=link_tree[cat_name][subcat])
        print (source_path)
        res_df = eda(get_all_prod_df(source_path))
        res_df['subcat'] = subcat
        all_res_df = all_res_df.append(res_df)
    all_res_df.to_csv(os.path.join(data_path,'res_cat.csv'))

if __name__ == "__main__":
    explore_cat()