import mysql.connector
import json
from tkinter import messagebox, Tk, Label, Button, Frame, Listbox, Scrollbar, VERTICAL, END, StringVar
from tkinter.ttk import Progressbar
import re
from difflib import SequenceMatcher

class AuthorDeduplicationTool:
    def __init__(self, root=None):
        self.config = None
        self.conn = None
        self.cursor = None
        self.duplicate_groups = []
        
        # If root is provided, create GUI
        if root:
            self.root = root
            self.root.title("Author Deduplication Tool")
            self.root.geometry("800x600")
            self.setup_gui()
    
    def setup_gui(self):
        # Main frame
        main_frame = Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Header
        Label(main_frame, text="Author Deduplication Tool", font=("Arial", 16, "bold")).pack(pady=(0, 20))
        
        # Buttons frame
        btn_frame = Frame(main_frame)
        btn_frame.pack(fill='x', pady=10)
        
        Button(btn_frame, text="Find Duplicates", command=self.find_duplicates, width=15).pack(side='left', padx=5)
        Button(btn_frame, text="Process All", command=self.process_all_duplicates, width=15).pack(side='left', padx=5)
        
        # Progress bar
        self.progress_var = StringVar()
        self.progress_var.set("Ready")
        self.progress_bar = Progressbar(main_frame, orient='horizontal', length=100, mode='determinate')
        self.progress_bar.pack(fill='x', pady=10)
        Label(main_frame, textvariable=self.progress_var).pack(pady=(0, 10))
        
        # Results frame
        results_frame = Frame(main_frame)
        results_frame.pack(fill='both', expand=True)
        
        # Duplicates list
        list_frame = Frame(results_frame)
        list_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        Label(list_frame, text="Duplicate Groups:").pack(anchor='w')
        
        self.duplicates_listbox = Listbox(list_frame)
        self.duplicates_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = Scrollbar(list_frame, orient=VERTICAL)
        scrollbar.config(command=self.duplicates_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.duplicates_listbox.config(yscrollcommand=scrollbar.set)
        
        # Details frame
        details_frame = Frame(results_frame)
        details_frame.pack(side='right', fill='both', expand=True)
        
        Label(details_frame, text="Author Details:").pack(anchor='w')
        
        self.details_listbox = Listbox(details_frame, height=10)
        self.details_listbox.pack(fill='both', expand=True)
        
        details_scrollbar = Scrollbar(details_frame, orient=VERTICAL)
        details_scrollbar.config(command=self.details_listbox.yview)
        details_scrollbar.pack(side='right', fill='y')
        
        self.details_listbox.config(yscrollcommand=details_scrollbar.set)
        
        # Action buttons
        action_frame = Frame(details_frame)
        action_frame.pack(fill='x', pady=10)
        
        Button(action_frame, text="Merge Selected", command=self.merge_selected).pack(side='left', padx=5)
        Button(action_frame, text="Keep Separate", command=self.keep_separate).pack(side='left', padx=5)
        
        # Bind selection event
        self.duplicates_listbox.bind('<<ListboxSelect>>', self.on_group_select)
    
    def load_config(self):
        try:
            with open('selected_config.json', 'r') as file:
                self.config = json.load(file)
                
            # Validate config fields
            required_keys = ["host", "database", "user", "password"]
            for key in required_keys:
                if key not in self.config or not str(self.config[key]).strip():
                    messagebox.showerror("Config Error", f"Missing or empty field: {key}")
                    return False
                    
            return True
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to load config: {e}")
            return False
    
    def connect_to_database(self):
        try:
            self.conn = mysql.connector.connect(
                host=self.config["host"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"]
            )
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except mysql.connector.Error as err:
            messagebox.showerror("Connection Error", f"Database connection failed: {err}")
            return False
    
    def find_duplicates(self):
        if not self.load_config() or not self.connect_to_database():
            return
            
        try:
            self.progress_var.set("Finding duplicates...")
            self.progress_bar['value'] = 10
            self.root.update()
            
            # First, check which columns exist in author_profile
            self.cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'author_profile'
            """)
            columns = [row['COLUMN_NAME'] for row in self.cursor.fetchall()]
            
            # Find duplicate names
            self.cursor.execute("""
                SELECT full_name, COUNT(*) AS cnt 
                FROM author_profile 
                GROUP BY full_name 
                HAVING cnt > 1
            """)
            duplicates = self.cursor.fetchall()
            
            self.progress_bar['value'] = 30
            self.root.update()
            
            # Clear previous results
            self.duplicate_groups = []
            self.duplicates_listbox.delete(0, END)
            self.details_listbox.delete(0, END)
            
            # Process each duplicate group
            total = len(duplicates)
            for i, row in enumerate(duplicates):
                full_name = row['full_name']
                count = row['cnt']
                
                # Get all authors with this name
                query = "SELECT author_id, full_name"
                
                # Add optional columns if they exist
                for col in ['article_number', 'workplace', 'research', 'email', 'bio', 'job', 'influence']:
                    if col in columns:
                        query += f", {col}"
                
                query += " FROM author_profile WHERE full_name = %s"
                
                self.cursor.execute(query, (full_name,))
                authors = self.cursor.fetchall()
                
                # Get article counts for each author
                for author in authors:
                    if 'article_number' not in author or author['article_number'] is None:
                        # Count articles from article_authors table
                        self.cursor.execute("""
                            SELECT COUNT(*) as article_count 
                            FROM article_authors 
                            WHERE author_id = %s
                        """, (author['author_id'],))
                        result = self.cursor.fetchone()
                        author['article_number'] = result['article_count'] if result else 0
                
                # Get co-author relationships if possible
                coauthor_data = self.get_coauthor_data(authors)
                
                # Calculate similarity scores between authors
                similarity_info = self.calculate_author_similarities(authors, coauthor_data, columns)
                
                # Add to our list of duplicate groups
                self.duplicate_groups.append({
                    'name': full_name,
                    'authors': authors,
                    'similarity': similarity_info,
                    'coauthor_data': coauthor_data
                })
                
                # Add to listbox
                self.duplicates_listbox.insert(END, f"{full_name} ({count} authors)")
                
                # Update progress
                self.progress_bar['value'] = 30 + (i / total * 70)
                self.progress_var.set(f"Processing {i+1} of {total}...")
                self.root.update()
            
            self.progress_bar['value'] = 100
            self.progress_var.set(f"Found {len(duplicates)} duplicate groups")
            
            messagebox.showinfo("Success", f"Found {len(duplicates)} groups of authors with the same name")
            
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Operation failed: {err}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    def get_coauthor_data(self, authors):
        """Get co-author data for similarity analysis"""
        coauthor_data = {}
        
        for author in authors:
            author_id = author['author_id']
            coauthor_data[author_id] = []
            
            try:
                # Get articles by this author
                self.cursor.execute("""
                    SELECT article_id 
                    FROM article_authors 
                    WHERE author_id = %s
                """, (author_id,))
                articles = self.cursor.fetchall()
                
                # Get co-authors for each article
                for article in articles:
                    article_id = article['article_id']
                    self.cursor.execute("""
                        SELECT author_id 
                        FROM article_authors 
                        WHERE article_id = %s AND author_id != %s
                    """, (article_id, author_id))
                    coauthors = self.cursor.fetchall()
                    coauthor_data[author_id].extend([ca['author_id'] for ca in coauthors])
            except:
                # If any error occurs, just continue with empty coauthor data
                pass
                
        return coauthor_data
    
    def calculate_author_similarities(self, authors, coauthor_data, available_columns):
        """Calculate similarity scores between all pairs of authors"""
        similarity_info = {
            'are_same_person': False,
            'confidence': 0,
            'reasons': [],
            'pairwise_scores': {}
        }
        
        # If only one author, no comparison needed
        if len(authors) <= 1:
            return similarity_info
        
        # For each pair of authors
        for i in range(len(authors)):
            for j in range(i+1, len(authors)):
                author1 = authors[i]
                author2 = authors[j]
                
                pair_key = f"{author1['author_id']}_{author2['author_id']}"
                score = 0
                reasons = []
                factors = 0
                
                # Compare optional fields if they exist
                for field in ['workplace', 'research', 'email', 'job']:
                    if field in available_columns and field in author1 and field in author2:
                        if author1[field] and author2[field]:
                            factors += 1
                            if self.similar_strings(str(author1[field]), str(author2[field])):
                                score += 25
                                reasons.append(f"Similar {field}")
                            else:
                                reasons.append(f"Different {field}")
                
                # Compare co-authors
                coauthors1 = set(coauthor_data.get(author1['author_id'], []))
                coauthors2 = set(coauthor_data.get(author2['author_id'], []))
                
                if coauthors1 and coauthors2:
                    factors += 2  # Give this more weight
                    
                    # Calculate Jaccard similarity
                    intersection = len(coauthors1.intersection(coauthors2))
                    union = len(coauthors1.union(coauthors2))
                    
                    if union > 0:
                        jaccard = intersection / union
                        coauthor_score = jaccard * 50  # Scale to 0-50
                        score += coauthor_score
                        
                        if jaccard > 0.5:
                            reasons.append(f"Strong co-author overlap ({intersection} shared)")
                        elif jaccard > 0:
                            reasons.append(f"Some co-author overlap ({intersection} shared)")
                        else:
                            reasons.append("No co-author overlap")
                
                # If we have article counts, authors with very different counts are less likely to be the same
                if 'article_number' in author1 and 'article_number' in author2:
                    count1 = author1['article_number'] or 0
                    count2 = author2['article_number'] or 0
                    
                    if count1 > 0 and count2 > 0:
                        factors += 1
                        ratio = min(count1, count2) / max(count1, count2) if max(count1, count2) > 0 else 0
                        
                        if ratio > 0.7:
                            score += 15
                            reasons.append(f"Similar article counts ({count1} vs {count2})")
                        elif ratio < 0.3 and max(count1, count2) > 5:
                            # Significant difference in productivity suggests different people
                            score -= 15
                            reasons.append(f"Very different article counts ({count1} vs {count2})")
                
                # Calculate final score
                final_score = score / max(factors, 1) if factors > 0 else 50  # Default to 50% if no factors
                
                similarity_info['pairwise_scores'][pair_key] = {
                    'score': final_score,
                    'reasons': reasons
                }
        
        # Determine overall similarity based on pairwise scores
        if similarity_info['pairwise_scores']:
            avg_score = sum(item['score'] for item in similarity_info['pairwise_scores'].values()) / len(similarity_info['pairwise_scores'])
            similarity_info['confidence'] = avg_score
            similarity_info['are_same_person'] = avg_score >= 70
            
            # Collect all unique reasons
            all_reasons = []
            for item in similarity_info['pairwise_scores'].values():
                for reason in item['reasons']:
                    if reason not in all_reasons:
                        all_reasons.append(reason)
            
            similarity_info['reasons'] = all_reasons
        
        return similarity_info
    
    def similar_strings(self, str1, str2, threshold=0.8):
        """Check if two strings are similar using sequence matcher"""
        if not str1 or not str2:
            return False
            
        # Clean and normalize strings
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # Calculate similarity ratio
        similarity = SequenceMatcher(None, str1, str2).ratio()
        return similarity >= threshold
    
    def on_group_select(self, event):
        """Handle selection of a duplicate group"""
        selection = self.duplicates_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        group = self.duplicate_groups[index]
        
        # Clear details listbox
        self.details_listbox.delete(0, END)
        
        # Add author details
        for author in group['authors']:
            self.details_listbox.insert(END, f"ID: {author['author_id']} - {author['full_name']}")
            
            # Add optional fields if they exist
            for field in ['workplace', 'research', 'email', 'job', 'bio']:
                if field in author and author[field]:
                    self.details_listbox.insert(END, f"  {field.capitalize()}: {author[field]}")
            
            # Always show article count (calculated if not in DB)
            self.details_listbox.insert(END, f"  Articles: {author.get('article_number', 0)}")
            
            # Show co-author count
            coauthor_count = len(set(group['coauthor_data'].get(author['author_id'], [])))
            if coauthor_count > 0:
                self.details_listbox.insert(END, f"  Co-authors: {coauthor_count}")
                
            self.details_listbox.insert(END, "")
        
        # Add similarity info
        similarity = group['similarity']
        self.details_listbox.insert(END, "Similarity Analysis:")
        self.details_listbox.insert(END, f"  Confidence: {similarity['confidence']:.1f}%")
        self.details_listbox.insert(END, f"  Likely same person: {'Yes' if similarity['are_same_person'] else 'No'}")
        
        for reason in similarity['reasons']:
            self.details_listbox.insert(END, f"  • {reason}")
    
    def merge_selected(self):
        """Merge the selected duplicate group"""
        selection = self.duplicates_listbox.curselection()
        if not selection:
            messagebox.showinfo("Selection Required", "Please select a duplicate group first")
            return
            
        index = selection[0]
        group = self.duplicate_groups[index]
        
        if not group['authors']:
            messagebox.showerror("Error", "No authors found in this group")
            return
            
        # Find the author with the most complete profile to keep
        keep_author = self.find_most_complete_profile(group['authors'])
        
        try:
            # Start transaction
            self.conn.start_transaction()
            
            # Update article counts
            total_articles = sum(author.get('article_number', 0) for author in group['authors'])
            
            # Check if article_number column exists
            self.cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'author_profile'
                AND COLUMN_NAME = 'article_number'
            """)
            has_article_number = bool(self.cursor.fetchone())
            
            # Update the author to keep if the column exists
            if has_article_number:
                self.cursor.execute("""
                    UPDATE author_profile 
                    SET article_number = %s 
                    WHERE author_id = %s
                """, (total_articles, keep_author['author_id']))
            
            # Update article_authors table to point to the kept author
            for author in group['authors']:
                if author['author_id'] != keep_author['author_id']:
                    self.cursor.execute("""
                        UPDATE article_authors 
                        SET author_id = %s 
                        WHERE author_id = %s
                    """, (keep_author['author_id'], author['author_id']))
            
            # Update correlation table if it exists
            try:
                # Check if correlation table exists
                self.cursor.execute("""
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'correlation'
                """)
                
                if self.cursor.fetchone():
                    # Update correlations where author1_id is being deleted
                    for author in group['authors']:
                        if author['author_id'] != keep_author['author_id']:
                            self.cursor.execute("""
                                UPDATE correlation 
                                SET author1_id = %s 
                                WHERE author1_id = %s
                            """, (keep_author['author_id'], author['author_id']))
                            
                            self.cursor.execute("""
                                UPDATE correlation 
                                SET author2_id = %s 
                                WHERE author2_id = %s
                            """, (keep_author['author_id'], author['author_id']))
                            
                            # Remove duplicate correlations that might have been created
                            self.cursor.execute("""
                                DELETE FROM correlation 
                                WHERE author1_id = author2_id
                            """)
            except:
                # If correlation table doesn't exist or other error, just continue
                pass
            
            # Delete other author profiles
            for author in group['authors']:
                if author['author_id'] != keep_author['author_id']:
                    self.cursor.execute("""
                        DELETE FROM author_profile 
                        WHERE author_id = %s
                    """, (author['author_id'],))
            
            # Commit transaction
            self.conn.commit()
            
            messagebox.showinfo("Success", f"Merged {len(group['authors'])} authors into ID: {keep_author['author_id']}")
            
            # Refresh the list
            self.find_duplicates()
            
        except mysql.connector.Error as err:
            self.conn.rollback()
            messagebox.showerror("Database Error", f"Merge failed: {err}")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    def find_most_complete_profile(self, authors):
        """Find the author with the most complete profile"""
        best_author = authors[0]
        best_score = 0
        
        for author in authors:
            score = 0
            
            # Add points for each non-empty field
            for field in ['workplace', 'email', 'research', 'bio', 'job']:
                if field in author and author[field]:
                    score += 1
            
            # Prefer authors with more articles
            article_count = author.get('article_number', 0) or 0
            score += min(article_count / 10, 5)  # Cap at 5 points
                
            # Prefer lower IDs (older records) as a tiebreaker
            score -= author['author_id'] / 1000000
                
            if score > best_score:
                best_score = score
                best_author = author
                
        return best_author
    
    def keep_separate(self):
        """Mark the selected duplicate group to be kept as separate authors"""
        selection = self.duplicates_listbox.curselection()
        if not selection:
            messagebox.showinfo("Selection Required", "Please select a duplicate group first")
            return
            
        messagebox.showinfo("Info", "Authors will be kept as separate individuals")
    
    def process_all_duplicates(self):
        """Process all duplicate groups automatically based on similarity"""
        if not self.duplicate_groups:
            messagebox.showinfo("No Data", "Please find duplicates first")
            return
            
        try:
            self.progress_var.set("Processing duplicates...")
            self.progress_bar['value'] = 0
            self.root.update()
            
            merged_count = 0
            kept_separate_count = 0
            
            # Check if article_number column exists
            self.cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'author_profile'
                AND COLUMN_NAME = 'article_number'
            """)
            has_article_number = bool(self.cursor.fetchone())
            
            for i, group in enumerate(self.duplicate_groups):
                similarity = group['similarity']
                
                # If confidence is high enough, merge
                if similarity['are_same_person'] and similarity['confidence'] >= 70:
                    # Find the author with the most complete profile
                    keep_author = self.find_most_complete_profile(group['authors'])
                    
                    # Start transaction
                    self.conn.start_transaction()
                    
                    try:
                        # Update article counts
                        total_articles = sum(author.get('article_number', 0) for author in group['authors'])
                        
                        # Update the author to keep if the column exists
                        if has_article_number:
                            self.cursor.execute("""
                                UPDATE author_profile 
                                SET article_number = %s 
                                WHERE author_id = %s
                            """, (total_articles, keep_author['author_id']))
                        
                        # Update article_authors table
                        for author in group['authors']:
                            if author['author_id'] != keep_author['author_id']:
                                self.cursor.execute("""
                                    UPDATE article_authors 
                                    SET author_id = %s 
                                    WHERE author_id = %s
                                """, (keep_author['author_id'], author['author_id']))
                        
                        # Update correlation table if it exists
                        try:
                            # Check if correlation table exists
                            self.cursor.execute("""
                                SELECT 1 
                                FROM information_schema.tables 
                                WHERE table_schema = DATABASE() 
                                AND table_name = 'correlation'
                            """)
                            
                            if self.cursor.fetchone():
                                # Update correlations where author1_id is being deleted
                                for author in group['authors']:
                                    if author['author_id'] != keep_author['author_id']:
                                        self.cursor.execute("""
                                            UPDATE correlation 
                                            SET author1_id = %s 
                                            WHERE author1_id = %s
                                        """, (keep_author['author_id'], author['author_id']))
                                        
                                        self.cursor.execute("""
                                            UPDATE correlation 
                                            SET author2_id = %s 
                                            WHERE author2_id = %s
                                        """, (keep_author['author_id'], author['author_id']))
                                        
                                        # Remove duplicate correlations that might have been created
                                        self.cursor.execute("""
                                            DELETE FROM correlation 
                                            WHERE author1_id = author2_id
                                        """)
                        except:
                            # If correlation table doesn't exist or other error, just continue
                            pass
                        
                        # Delete other author profiles
                        for author in group['authors']:
                            if author['author_id'] != keep_author['author_id']:
                                self.cursor.execute("""
                                    DELETE FROM author_profile 
                                    WHERE author_id = %s
                                """, (author['author_id'],))
                        
                        self.conn.commit()
                        merged_count += 1
                    except:
                        self.conn.rollback()
                        raise
                else:
                    kept_separate_count += 1
                
                # Update progress
                self.progress_bar['value'] = (i + 1) / len(self.duplicate_groups) * 100
                self.progress_var.set(f"Processing {i+1} of {len(self.duplicate_groups)}...")
                self.root.update()
            
            self.progress_bar['value'] = 100
            self.progress_var.set("Processing complete")
            
            messagebox.showinfo("Processing Complete", 
                               f"Merged: {merged_count} groups\n"
                               f"Kept separate: {kept_separate_count} groups")
            
            # Refresh the list
            self.find_duplicates()
            
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Operation failed: {err}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()

def main():
    root = Tk()
    app = AuthorDeduplicationTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()

