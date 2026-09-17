/*SELECT typeof(embedding), COUNT(*) 
FROM posts 
GROUP BY typeof(embedding);*/

SELECT id, title, typeof(embedding) 
FROM posts 
WHERE typeof(embedding) = 'text';