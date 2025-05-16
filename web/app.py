from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import mysql.connector
import json
# from mysql.connector import pooling
from collections import defaultdict
import re
import os
import hashlib
import uuid
from functools import wraps
import logging
from model import GNN, Dataloader
import pickle
import torch
from tokenizers import Tokenizer
from flask import Flask, request, send_from_directory, jsonify, render_template, session


app = Flask(__name__)


N_AUTHOR_SEARCH = 16
N_TOP_RESULTS = 15
N_HOPS_NEIGHBORHOOD = 3
N_MIN_NODES = 1000

with open("resources/edges.pkl", "rb") as file:
    edges = pickle.load(file)
with open("resources/features.pkl", "rb") as file:
    features = pickle.load(file)
with open("resources/author_citations.pkl", "rb") as file:
    author_citations = pickle.load(file)
# with open("resources/papers_by_author.pkl", "rb") as file:
#     papers_by_author = pickle.load(file)
with open("resources/authors.pkl", "rb") as file:
    author2id = pickle.load(file)
    id2author = {v: k for k, v in author2id.items()}
with open("resources/keywords.pkl", "rb") as file:
    keyword2id = pickle.load(file)
    id2keyword = {v: k for k, v in keyword2id.items()}
tokenizer = Tokenizer.from_file("resources/tokenizer.json")

dataloader = Dataloader(edges=edges,
                        features=features,
                        tokenizer=tokenizer,
                        k_hops=N_HOPS_NEIGHBORHOOD,
                        n_min_nodes=N_MIN_NODES)
model = GNN(n_tokens=tokenizer.get_vocab_size(),
            n_keywords=len(keyword2id),
            n_authors=len(author2id))
weights = torch.load("resources/model.pt", map_location="cpu")
model.load_state_dict(weights)
del weights

def bad_request(message):
    response = jsonify({"error": message})
    response.status_code = 400
    return response

# connect to database
def get_db_config():
    # Get the current working directory
    current_directory = os.getcwd()

    # Get the parent directory of the current directory
    parent_directory = os.path.dirname(current_directory)

    # Construct the path to selected_config.json
    config_file_path = os.path.join(parent_directory, 'database', 'selected_config.json')
    # config_file_path = os.path.join('database', 'selected_config.json')

    # Read the JSON configuration file
    with open(config_file_path, 'r') as f:
        return json.load(f)
    
# 创建连接池
connection_pool = mysql.connector.pooling.MySQLConnectionPool(**get_db_config())

# app.py
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html'), 500

@app.route('/')
def home():
    return render_template('homepage.html', template_name='homepage.html')


@app.route('/web')
def web():
    query = request.args.get('query', '')
    return render_template('web.html', query=query)


@app.route('/search', methods=['GET'])
def search():
    search_query = request.args.get('query', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    if not search_query:
        return jsonify({"error": "Search query cannot be empty"}), 400

    connection = None
    cursor = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        offset = (page - 1) * per_page

        # Create search terms for better matching
        exact_term = search_query
        like_term = f"%{search_query}%"
        
        # For MATCH AGAINST, extract important keywords
        words = search_query.split()
        
        # Create different keyword combinations for better matching
        if len(words) > 5:
            # For long queries, create multiple keyword combinations
            keyword_sets = [
                # First 3 words (often most important)
                ' '.join(words[:3]),
                # Last 3 words
                ' '.join(words[-3:]),
                # Every other word to capture spread
                ' '.join(words[::2]),
                # Longer words (often more significant)
                ' '.join([w for w in words if len(w) > 5])
            ]
            fulltext_term = ' '.join([f'"{ks}"' for ks in keyword_sets if ks])
        else:
            # For shorter queries, use all words with wildcards
            fulltext_term = ' '.join([f'{w}*' for w in words if len(w) > 2])

        # Improved SQL query with better handling of long titles
        sql_query = """
        SELECT 
            a.id AS article_id,
            a.title,
            a.abstract,
            a.published_date,
            COALESCE(
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'id', aut.id,
                        'full_name', aut.full_name,
                        'bio', COALESCE(ap.bio, ''),
                        'workplace', COALESCE(ap.workplace, '')
                    )
                ),
                JSON_ARRAY()
            ) AS authors,
            (
                CASE 
                    WHEN LOWER(a.title) = LOWER(%s) THEN 100  /* Exact title match (case insensitive) */
                    WHEN LOWER(a.title) LIKE LOWER(%s) THEN 70  /* Title contains query (case insensitive) */
                    WHEN MATCH(a.title) AGAINST (%s IN BOOLEAN MODE) THEN 60  /* Fulltext title match */
                    /* Calculate word match percentage for long titles */
                    WHEN (
                        SELECT COUNT(*) FROM (
                            SELECT UNNEST(REGEXP_SPLIT_TO_ARRAY(LOWER(%s), '\\s+')) AS word
                        ) AS words
                        WHERE LOWER(a.title) LIKE CONCAT('%%', word, '%%')
                    ) > LENGTH(%s) / 20 THEN 40  /* At least 5% of words match */
                    ELSE 0 
                END +
                /* Use MAX() for author-related scores to make them GROUP BY compatible */
                MAX(
                    CASE 
                        WHEN LOWER(aut.full_name) = LOWER(%s) THEN 100  /* Exact author match */
                        WHEN LOWER(aut.full_name) LIKE LOWER(%s) THEN 60  /* Author name contains query */
                        WHEN MATCH(aut.full_name) AGAINST (%s IN BOOLEAN MODE) THEN 30  /* Fulltext author match */
                        ELSE 0 
                    END
                ) +
                CASE 
                    WHEN MATCH(a.content) AGAINST (%s IN BOOLEAN MODE) THEN 20  /* Content match */
                    ELSE 0 
                END
            ) AS relevance_score
        FROM articles a
        LEFT JOIN article_authors aa ON a.id = aa.article_id
        LEFT JOIN authors aut ON aa.author_id = aut.id
        LEFT JOIN author_profile ap ON aut.id = ap.author_id
        WHERE 
            LOWER(a.title) = LOWER(%s) OR  /* Exact title match (case insensitive) */
            LOWER(a.title) LIKE LOWER(%s) OR  /* Title contains query (case insensitive) */
            MATCH(a.title) AGAINST (%s IN BOOLEAN MODE) OR  /* Fulltext title match */
            /* Word-by-word matching for long titles */
            (LENGTH(%s) > 30 AND (
                SELECT COUNT(*) FROM (
                    SELECT UNNEST(REGEXP_SPLIT_TO_ARRAY(LOWER(%s), '\\s+')) AS word
                ) AS words
                WHERE LOWER(a.title) LIKE CONCAT('%%', word, '%%')
            ) > LENGTH(%s) / 20) OR  /* At least 5% of words match */
            LOWER(aut.full_name) = LOWER(%s) OR  /* Exact author match */
            LOWER(aut.full_name) LIKE LOWER(%s) OR  /* Author name contains query */
            MATCH(aut.full_name) AGAINST (%s IN BOOLEAN MODE) OR  /* Fulltext author match */
            MATCH(a.content) AGAINST (%s IN BOOLEAN MODE)  /* Content match */
        GROUP BY a.id, a.title, a.abstract, a.published_date
        ORDER BY relevance_score DESC, a.published_date DESC
        LIMIT %s OFFSET %s;
        """

        # Parameters for the query
        params = (
            # Relevance scoring parameters
            exact_term,      # Exact title match
            like_term,       # Title contains query
            fulltext_term,   # Fulltext title match
            exact_term,      # For word-by-word matching
            exact_term,      # For length calculation
            exact_term,      # Exact author match
            like_term,       # Author name contains query
            fulltext_term,   # Fulltext author match
            fulltext_term,   # Content match
            
            # WHERE clause parameters
            exact_term,      # Exact title match
            like_term,       # Title contains query
            fulltext_term,   # Fulltext title match
            exact_term,      # For length check
            exact_term,      # For word-by-word matching
            exact_term,      # For length calculation
            exact_term,      # Exact author match
            like_term,       # Author name contains query
            fulltext_term,   # Fulltext author match
            fulltext_term,   # Content match
            
            per_page,        # LIMIT
            offset           # OFFSET
        )
        
        # Check if MySQL supports REGEXP_SPLIT_TO_ARRAY and UNNEST
        # If not, use a simpler fallback query
        try:
            cursor.execute(sql_query, params)
            articles = cursor.fetchall()
        except mysql.connector.Error as err:
            if "REGEXP_SPLIT_TO_ARRAY" in str(err) or "UNNEST" in str(err):
                # Fallback to simpler query without word-by-word matching
                fallback_query = """
                SELECT 
                    a.id AS article_id,
                    a.title,
                    a.abstract,
                    a.published_date,
                    COALESCE(
                        JSON_ARRAYAGG(
                            JSON_OBJECT(
                                'id', aut.id,
                                'full_name', aut.full_name,
                                'bio', COALESCE(ap.bio, ''),
                                'workplace', COALESCE(ap.workplace, '')
                            )
                        ),
                        JSON_ARRAY()
                    ) AS authors,
                    (
                        CASE 
                            WHEN LOWER(a.title) = LOWER(%s) THEN 100  /* Exact title match */
                            WHEN LOWER(a.title) LIKE LOWER(%s) THEN 70  /* Title contains query */
                            WHEN MATCH(a.title) AGAINST (%s IN BOOLEAN MODE) THEN 60  /* Fulltext title match */
                            ELSE 0 
                        END +
                        MAX(
                            CASE 
                                WHEN LOWER(aut.full_name) = LOWER(%s) THEN 100  /* Exact author match */
                                WHEN LOWER(aut.full_name) LIKE LOWER(%s) THEN 60  /* Author name contains query */
                                WHEN MATCH(aut.full_name) AGAINST (%s IN BOOLEAN MODE) THEN 30  /* Fulltext author match */
                                ELSE 0 
                            END
                        ) +
                        CASE 
                            WHEN MATCH(a.content) AGAINST (%s IN BOOLEAN MODE) THEN 20  /* Content match */
                            ELSE 0 
                        END
                    ) AS relevance_score
                FROM articles a
                LEFT JOIN article_authors aa ON a.id = aa.article_id
                LEFT JOIN authors aut ON aa.author_id = aut.id
                LEFT JOIN author_profile ap ON aut.id = ap.author_id
                WHERE 
                    LOWER(a.title) = LOWER(%s) OR  /* Exact title match */
                    LOWER(a.title) LIKE LOWER(%s) OR  /* Title contains query */
                    MATCH(a.title) AGAINST (%s IN BOOLEAN MODE) OR  /* Fulltext title match */
                    LOWER(aut.full_name) = LOWER(%s) OR  /* Exact author match */
                    LOWER(aut.full_name) LIKE LOWER(%s) OR  /* Author name contains query */
                    MATCH(aut.full_name) AGAINST (%s IN BOOLEAN MODE) OR  /* Fulltext author match */
                    MATCH(a.content) AGAINST (%s IN BOOLEAN MODE)  /* Content match */
                GROUP BY a.id, a.title, a.abstract, a.published_date
                ORDER BY relevance_score DESC, a.published_date DESC
                LIMIT %s OFFSET %s;
                """
                
                fallback_params = (
                    # Relevance scoring parameters
                    exact_term,      # Exact title match
                    like_term,       # Title contains query
                    fulltext_term,   # Fulltext title match
                    exact_term,      # Exact author match
                    like_term,       # Author name contains query
                    fulltext_term,   # Fulltext author match
                    fulltext_term,   # Content match
                    
                    # WHERE clause parameters
                    exact_term,      # Exact title match
                    like_term,       # Title contains query
                    fulltext_term,   # Fulltext title match
                    exact_term,      # Exact author match
                    like_term,       # Author name contains query
                    fulltext_term,   # Fulltext author match
                    fulltext_term,   # Content match
                    
                    per_page,        # LIMIT
                    offset           # OFFSET
                )
                
                cursor.execute(fallback_query, fallback_params)
                articles = cursor.fetchall()
            else:
                # Re-raise if it's a different error
                raise

        # If no results found with the complex query, try a simpler approach
        if not articles and len(search_query) > 30:
            # For very long queries, try matching individual words
            words = [w for w in search_query.split() if len(w) > 3]
            if words:
                # Take up to 5 significant words
                significant_words = words[:5]
                like_conditions = []
                params = []
                
                for word in significant_words:
                    like_conditions.append("LOWER(a.title) LIKE LOWER(%s)")
                    params.append(f"%{word}%")
                
                simple_query = f"""
                SELECT 
                    a.id AS article_id,
                    a.title,
                    a.abstract,
                    a.published_date,
                    COALESCE(
                        JSON_ARRAYAGG(
                            JSON_OBJECT(
                                'id', aut.id,
                                'full_name', aut.full_name,
                                'bio', COALESCE(ap.bio, ''),
                                'workplace', COALESCE(ap.workplace, '')
                            )
                        ),
                        JSON_ARRAY()
                    ) AS authors
                FROM articles a
                LEFT JOIN article_authors aa ON a.id = aa.article_id
                LEFT JOIN authors aut ON aa.author_id = aut.id
                LEFT JOIN author_profile ap ON aut.id = ap.author_id
                WHERE {" OR ".join(like_conditions)}
                GROUP BY a.id, a.title, a.abstract, a.published_date
                LIMIT %s OFFSET %s
                """
                
                params.extend([per_page, offset])
                cursor.execute(simple_query, params)
                articles = cursor.fetchall()

        # Convert JSON strings to Python objects
        for article in articles:
            if isinstance(article['authors'], str):
                article['authors'] = json.loads(article['authors'])

        return jsonify(articles)

    except mysql.connector.Error as err:
        app.logger.error(f"MySQL Error: {err}")
        return jsonify({"error": "Database operation failed"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if cursor: cursor.close()
        if connection and connection.is_connected(): 
            connection.close()



@app.route('/article/<int:article_id>')
def article_detail(article_id):
    connection = None
    cursor = None
    with open('/Users/hxh/Desktop/Research-Search-System/web/static/css/graph_model.json', 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # 获取文章基本信息
        article_query = """
            SELECT a.*, 
                   GROUP_CONCAT(DISTINCT aut.full_name SEPARATOR ', ') AS authors
            FROM articles a
            LEFT JOIN article_authors aa ON a.id = aa.article_id
            LEFT JOIN authors aut ON aa.author_id = aut.id
            WHERE a.id = %s
            GROUP BY a.id
        """
        cursor.execute(article_query, (article_id,))
        article = cursor.fetchone()

        if not article:
            return render_template('404.html'), 404

        authors_query = """
            SELECT aut.*, ap.bio, ap.workplace, ap.email, ap.research
            FROM authors aut
            LEFT JOIN author_profile ap ON aut.id = ap.author_id
            WHERE aut.id IN (
                SELECT author_id FROM article_authors WHERE article_id = %s
            )
        """
        cursor.execute(authors_query, (article_id,))
        authors = cursor.fetchall()

        #  article_id related edges
        article_key = next((a['key'] for a in graph_data['articles'] if a.get('id') == article_id), None)
        edges = [e for e in graph_data['edges'] if article_key and (e['source'] == article_key or e['target'] == article_key)]

        # node information
        related_node_ids = {node for edge in edges for node in (edge['source'], edge['target']) if node != article_key}

        # article_id node insert in related_node_ids
        related_node_ids.add(article_key)

        related_nodes = [article for article in graph_data['articles'] if article['key'] in related_node_ids]

        edge_set = set(tuple(sorted([edge['source'], edge['target']])) for edge in edges)

        #reference between related_nodes
        # for node in related_nodes:
        #     for other_node in related_nodes:
        #         if node['key'] != other_node['key']:
        #             # 检查是否存在互相引用
        #             if any(edge['source'] == node['key'] and edge['target'] == other_node['key'] for edge in graph_data['edges']) and \
        #                     any(edge['source'] == other_node['key'] and edge['target'] == node['key'] for edge in graph_data['edges']):
        #                 # 添加这条引用关系到 edge_set 中（避免重复）
        #                 edge_set.add(tuple(sorted([node['key'], other_node['key']])))
        #                 print(tuple(sorted([node['key'], other_node['key']])))
        #
        #
        # edges = [{'source': edge[0], 'target': edge[1]} for edge in edge_set]

        #return render_template('article_detail.html', article=article, authors=authors)
        return render_template('article_detail.html', article=article, authors=authors, edges=edges, nodes=related_nodes)
    except Exception as e:
        app.logger.error(f"Error fetching article details: {str(e)}")
        return render_template('error.html'), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



def find_related_authors(main_author):
    """根据作者信息查找所有可能关联的作者ID"""
    connection = connection_pool.get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # 基础查询：匹配全名
        base_query = """
            SELECT 
                a.id,
                a.full_name,
                ap.email,
                ap.workplace,
                ap.research
            FROM authors a
            LEFT JOIN author_profile ap ON a.id = ap.author_id
            WHERE a.full_name = %s
        """
        cursor.execute(base_query, (main_author['full_name'],))
        candidates = cursor.fetchall()

        # 过滤逻辑
        related_ids = []
        for candidate in candidates:
            # 匹配规则优先级
            match_score = 0
            
            # 规则1：邮箱完全匹配
            if main_author.get('email') and candidate.get('email'):
                if main_author['email'] == candidate['email']:
                    related_ids.append(candidate['id'])
                    continue  # 邮箱相同直接确认
                   
            # 规则2：工作单位和研究领域同时匹配
            if (main_author.get('workplace') and candidate.get('workplace') and
                main_author.get('research') and candidate.get('research')):
                if (main_author['workplace'] == candidate['workplace'] and
                    main_author['research'] == candidate['research']):
                    match_score += 2
                    
            # 规则3：工作单位单字段匹配
            elif main_author.get('workplace') and candidate.get('workplace'):
                if main_author['workplace'] == candidate['workplace']:
                    match_score += 1
                    
            # 最终判断
            if match_score >= 1 or (not main_author.get('email') and not main_author.get('workplace')):
                related_ids.append(candidate['id'])

        return list(set(related_ids))  # 去重

    finally:
        cursor.close()
        connection.close()

@app.route('/author/<int:author_id>')
def author_detail(author_id):
    try:
        # 获取主作者信息
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 获取基础信息
        cursor.execute("""
            SELECT a.*, ap.email, ap.workplace, ap.research 
            FROM authors a
            LEFT JOIN author_profile ap ON a.id = ap.author_id
            WHERE a.id = %s
        """, (author_id,))
        main_author = cursor.fetchone()

        if not main_author:
            return render_template('404.html'), 404

        # 查找所有关联作者ID
        related_author_ids = find_related_authors(main_author)
        
        # 获取所有关联文章
        articles_query = """
            SELECT DISTINCT a.* 
            FROM articles a
            JOIN article_authors aa ON a.id = aa.article_id
            WHERE aa.author_id IN ({})
            ORDER BY a.published_date DESC
        """.format(','.join(['%s']*len(related_author_ids)))
        
        cursor.execute(articles_query, related_author_ids)
        articles = cursor.fetchall()

        # 合并统计数据
        main_author['article_count'] = len(articles)
        main_author['related_authors_count'] = len(related_author_ids)

        return render_template('author_detail.html', 
                            author=main_author,
                            articles=articles)

    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return render_template('error.html'), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/authors')
def authors():
    connection = None
    cursor = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # 获取所有作者信息
        cursor.execute("SELECT id, full_name FROM authors ORDER BY full_name")
        authors = cursor.fetchall()

        # 按首字母分组
        authors_dict = defaultdict(list)
        other_authors = []  # 存放非英文字母开头的作者

        for author in authors:
            if author['full_name']:
                initial = author['full_name'][0].upper()
                # 检查是否为英文字母（A-Z），否则归入 #
                if re.match(r'[A-Z]', initial):
                    authors_dict[initial].append(author)
                else:
                    other_authors.append(author)
            else:
                other_authors.append(author)

        return render_template('authors.html', authors_dict=authors_dict, other_authors=other_authors)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return render_template('error.html'), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/prediction')
def predict():
    return render_template( "prediction.html")


@app.route("/predict", methods=["POST"])
def get_prediction():
    args = request.get_json()

    if "author" not in args:
        return bad_request("Please enter an author.")
    author = " ".join(x.capitalize() for x in args["author"].split())
    if author not in author2id:
        return bad_request("Invalid Author.")
    author_id = author2id[author]

    text = args["text"].strip()
    if "text" not in args or len(text) == 0:
        return bad_request("Please enter a text.")

    try:
        node_ids, adjacencies, text, keywords, keyword_mask = dataloader.get(author_id, text)
        predictions, keyword_attention = model.forward(node_ids, adjacencies, text, keywords, keyword_mask)

        top_adjacent, top_non_adjacent, top_keywords = [], [], []

        for argument in predictions.argsort(descending=True):
            node_id = node_ids[1 + argument].item()
            author = id2author[node_id]
            if len(top_adjacent) < N_TOP_RESULTS and node_id in edges[author_id]:
                top_adjacent.append(author)
            if len(top_non_adjacent) < N_TOP_RESULTS and node_id not in edges[author_id]:
                top_non_adjacent.append(author)
            if len(top_adjacent) == N_TOP_RESULTS and len(top_non_adjacent) == N_TOP_RESULTS:
                break

        for argument in keyword_attention.argsort(descending=True)[:N_TOP_RESULTS]:
            keyword = id2keyword[argument.item()]
            keyword = " ".join(x.capitalize() for x in keyword.split())
            top_keywords.append(keyword)

        return {
            "num_nodes": node_ids.shape[0],
            "num_hops": N_HOPS_NEIGHBORHOOD + 2,  # 2 GNN layers
            "adjacent_authors": top_adjacent,
            "non_adjacent_authors": top_non_adjacent,
            "keywords": top_keywords,
        }

        #渲染模板，将数据传入
        return render_template("prediction_result.html", **prediction_data)
    except:
        return bad_request("Error during prediction.")

@app.route('/prediction_result')
def prediction_result():
    return render_template('prediction_result.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    query = request.args.get('query', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    connection = None
    cursor = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        
        # 使用LIKE而不是MATCH AGAINST
        sql_query = """
        (SELECT title AS suggestion FROM articles 
         WHERE title LIKE %s LIMIT 5)
        UNION
        (SELECT full_name AS suggestion FROM authors 
         WHERE full_name LIKE %s LIMIT 5)
        ORDER BY suggestion
        LIMIT 8
        """
        
        # 准备LIKE查询参数
        search_pattern = f"%{query}%"
        
        cursor.execute(sql_query, (search_pattern, search_pattern))
        results = cursor.fetchall()
        
        # 提取建议列表
        suggestions = [result[0] for result in results]
        
        # 按相关性排序（以查询开头的优先）
        suggestions.sort(
            key=lambda x: (0 if x.lower().startswith(query.lower()) else 1, x)
        )
        
        return jsonify(suggestions)
        
    except mysql.connector.Error as err:
        app.logger.error(f"MySQL Error in suggestions: {err}")
        return jsonify([]), 500
    except Exception as e:
        app.logger.error(f"Error in suggestions: {str(e)}")
        return jsonify([]), 500
    finally:
        if cursor: cursor.close()
        if connection and connection.is_connected(): 
            connection.close()





# 哈希密码
def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

# 验证密码
def verify_password(password, hashed_password, salt):
    return hash_password(password, salt)[0] == hashed_password

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 全局上下文处理器，为所有模板提供用户信息
@app.context_processor
def inject_user():
    user_info = None
    if 'user_id' in session:
        try:
            db = connection_pool.get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute('SELECT id, email FROM users WHERE id = %s', (session['user_id'],))
            user_info = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching user info: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'db' in locals() and db:
                db.close()
    
    return dict(user_info=user_info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # 返回登录页面
    try:
        # 确保请求是 JSON
        if not request.is_json:
            return jsonify({'message': 'Invalid content type. Expected application/json'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'message': 'Invalid JSON format'}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400

        # 获取数据库连接
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)

        # 查询用户
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'message': 'Invalid email or password'}), 401

        # 验证密码
        if not verify_password(password, user['password'], user['salt']):
            return jsonify({'message': 'Invalid email or password'}), 401

        # 设置会话
        session['user_id'] = user['id']
        session['email'] = email

        return jsonify({'message': 'Login successful', 'redirect': '/?login_success=true'})

    except Exception as e:
        return jsonify({'message': f'Error during login: {str(e)}'}), 500

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()  # 归还连接

@app.route('/signup', methods=['POST'])
def signup():
    logging.debug("Signup request received")
    try:
        if not request.is_json:
            logging.debug("Invalid content type")
            return jsonify({'message': 'Invalid content type. Expected application/json'}), 400

        data = request.get_json()
        if not data:
            logging.debug("Invalid JSON format")
            return jsonify({'message': 'Invalid JSON format'}), 400

        email = data.get('email')
        password = data.get('password')
        logging.debug(f"Email: {email}, Password: {'*' * len(password) if password else ''}")

        if not email or not password:
            logging.debug("Email and password are required")
            return jsonify({'message': 'Email and password are required'}), 400

        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)

        logging.debug(f"Checking if email '{email}' exists")
        cursor.execute('SELECT 1 FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            logging.debug(f"Email '{email}' already registered")
            return jsonify({'message': 'Email already registered'}), 400

        user_id = str(uuid.uuid4())
        hashed_password, salt = hash_password(password)
        logging.debug(f"Generated user_id: {user_id}")
        logging.debug(f"Hashed password: {hashed_password}, Salt: {salt}")

        insert_user_sql = 'INSERT INTO users (id, email, password, salt) VALUES (%s, %s, %s, %s)'
        logging.debug(f"Executing SQL: {insert_user_sql} with params: {(user_id, email, hashed_password, salt)}")
        cursor.execute(insert_user_sql, (user_id, email, hashed_password, salt))

        insert_profile_sql = 'INSERT INTO profiles (user_id) VALUES (%s)'
        logging.debug(f"Executing SQL: {insert_profile_sql} with params: {(user_id,)}")
        cursor.execute(insert_profile_sql, (user_id,))

        db.commit()
        logging.debug("Signup successful")
        return jsonify({'message': 'Signup successful', 'redirect': '/login'})

    except Exception as e:
        logging.error(f"Error creating account: {str(e)}", exc_info=True)
        if 'db' in locals():
            db.rollback()
        return jsonify({'message': f'Error creating account: {str(e)}'}), 500

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()       

# 仪表板路由
@app.route('/library')
@login_required
def library():
    # Generate a color for the user avatar based on email
    email = session.get('email', '')
    hash_value = 0
    for i in range(len(email)):
        hash_value = ord(email[i]) + ((hash_value << 5) - hash_value)
    hue = hash_value % 360
    user_color = f"hsl({hue}, 65%, 50%)"

    # Get recent searches if needed
    recent_searches = []
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT * FROM search_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 5',
            (session['user_id'],)
        )
        recent_searches = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching recent searches: {str(e)}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()

    return render_template('library.html', user_color=user_color, recent_searches=recent_searches)

# 用户API路由
@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'message': 'Not logged in'}), 401

    user_id = session['user_id']
    email = session['email']

    # Get recent searches if needed
    recent_searches = []
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT * FROM search_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 5',
            (user_id,)
        )
        recent_searches = cursor.fetchall()
        
        # Convert to JSON serializable format
        searches = []
        for search in recent_searches:
            searches.append({
                'id': search['id'],
                'query': search['query'],
                'timestamp': search['created_at'].isoformat() if hasattr(search['created_at'], 'isoformat') else search['created_at']
            })
    except Exception as e:
        print(f"Error fetching recent searches: {str(e)}")
        searches = []
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()

    return jsonify({
        'id': user_id,
        'email': email,
        'recentSearches': searches
    })

# 注销路由
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'})

# 收藏相关API
@app.route('/api/favorites')
@login_required
def get_favorites():
    user_id = session['user_id']
    favorites = []
    
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT article_id FROM favorites WHERE user_id = %s',
            (user_id,)
        )
        results = cursor.fetchall()
        
        favorites = [item['article_id'] for item in results]
    except Exception as e:
        print(f"Error fetching favorites: {str(e)}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()
    
    return jsonify(favorites)

@app.route('/api/favorite/<article_id>', methods=['POST'])
@login_required
def add_favorite(article_id):
    user_id = session['user_id']
    
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor()
        
        # 检查是否已经收藏
        cursor.execute(
            'SELECT 1 FROM favorites WHERE user_id = %s AND article_id = %s',
            (user_id, article_id)
        )
        if cursor.fetchone():
            return jsonify({'message': 'Already favorited'}), 400
        
        # Generate a unique ID for the favorite
        favorite_id = str(uuid.uuid4())
        
        # 添加收藏
        cursor.execute(
            'INSERT INTO favorites (id, user_id, article_id) VALUES (%s, %s, %s)',
            (favorite_id, user_id, article_id)
        )
        db.commit()
        
        return jsonify({'message': 'Article favorited successfully'})
    except Exception as e:
        if 'db' in locals():
            db.rollback()
        app.logger.error(f"Error adding favorite: {str(e)}")
        return jsonify({'message': f'Error adding favorite: {str(e)}'}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()

            
@app.route('/api/unfavorite/<article_id>', methods=['POST'])
def remove_favorite(article_id):
    """
    Remove an article from the user's favorites.
    
    Args:
        article_id: The ID of the article to unfavorite
        
    Returns:
        JSON response indicating success or failure
    """
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'message': 'Authentication required', 'error': 'not_authenticated'}), 401
    
    user_id = session['user_id']
    
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor()
        
        # Log the request for debugging
        app.logger.info(f"Removing favorite: user_id={user_id}, article_id={article_id}")
        
        # Check if the favorite exists
        cursor.execute(
            'SELECT 1 FROM favorites WHERE user_id = %s AND article_id = %s',
            (user_id, article_id)
        )
        if not cursor.fetchone():
            app.logger.warning(f"Favorite not found: user_id={user_id}, article_id={article_id}")
            return jsonify({'message': 'Favorite not found'}), 404
        
        # Remove the favorite
        cursor.execute(
            'DELETE FROM favorites WHERE user_id = %s AND article_id = %s',
            (user_id, article_id)
        )
        db.commit()
        
        app.logger.info(f"Favorite removed successfully: user_id={user_id}, article_id={article_id}")
        return jsonify({'success': True, 'message': 'Article removed from favorites successfully'}), 200
    except Exception as e:
        if 'db' in locals():
            db.rollback()
        app.logger.error(f"Error removing favorite: user_id={user_id}, article_id={article_id}, error={str(e)}")
        return jsonify({'message': f'Error removing favorite: {str(e)}'}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()

@app.route('/api/favorites/details')
@login_required
def get_favorites_details():
    user_id = session['user_id']
    favorites = []
    
    try:
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)
        
        # Get favorited articles with details
        query = """
        SELECT f.id as favorite_id, f.article_id, a.title, a.abstract, a.published_date,
               GROUP_CONCAT(DISTINCT aut.full_name SEPARATOR ', ') as authors
        FROM favorites f
        JOIN articles a ON f.article_id = a.id
        LEFT JOIN article_authors aa ON a.id = aa.article_id
        LEFT JOIN authors aut ON aa.author_id = aut.id
        WHERE f.user_id = %s
        GROUP BY f.id, f.article_id, a.title, a.abstract, a.published_date
        ORDER BY f.created_at DESC
        """
        
        cursor.execute(query, (user_id,))
        favorites = cursor.fetchall()
        
        # Format dates for JSON serialization
        for favorite in favorites:
            if favorite['published_date']:
                favorite['published_date'] = favorite['published_date'].strftime('%Y-%m-%d')
        
        return jsonify(favorites)
    except Exception as e:
        app.logger.error(f"Error fetching favorite details: {str(e)}")
        return jsonify({"error": f"Error fetching favorites: {str(e)}"}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()



@app.route('/favorites')
@login_required
def favorites_page():
    """Renders the favorites.html page."""
    if 'user_id' not in session:
        return redirect(url_for('login', redirect='/favorites'))
    return render_template('favorites.html')


# 在所有模板中包含认证组件
@app.template_filter('include_auth')
def include_auth(template_name):
    # 排除错误页面和特定页面
    excluded_templates = ['error.html', '404.html', '500.html']
    if template_name not in excluded_templates:
        return True
    return False

@app.route('/management')
@login_required
def management_page():
    """Renders the management.html page."""
    if 'user_id' not in session:
        return redirect(url_for('login', redirect='/management'))
    return render_template('management.html')

# 添加这个新的 API 路由用于密码更新
@app.route('/api/update-password', methods=['PUT'])
@login_required
def update_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        current_password = data.get('current')
        new_password = data.get('new')
        confirm_password = data.get('confirm')
        
        # 验证输入
        if not current_password or not new_password or not confirm_password:
            return jsonify({"error": "All fields are required"}), 400
        
        if new_password != confirm_password:
            return jsonify({"error": "New passwords do not match"}), 400
        
        if len(new_password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        
        # 获取用户信息
        db = connection_pool.get_connection()
        cursor = db.cursor(dictionary=True)
        
        # 获取当前用户
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # 验证当前密码
        if not verify_password(current_password, user['password'], user['salt']):
            return jsonify({"error": "Current password is incorrect"}), 400
        
        # 更新密码
        hashed_password, salt = hash_password(new_password)
        cursor.execute(
            'UPDATE users SET password = %s, salt = %s WHERE id = %s',
            (hashed_password, salt, session['user_id'])
        )
        db.commit()
        
        return jsonify({"success": True, "message": "Password updated successfully"})
        
    except Exception as e:
        app.logger.error(f"Error updating password: {str(e)}")
        if 'db' in locals():
            db.rollback()
        return jsonify({"error": f"Failed to update password: {str(e)}"}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()

if __name__ == '__main__':
    app.run(debug=True)