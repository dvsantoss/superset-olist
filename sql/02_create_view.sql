-- Uma linha por item vendido, já com pedido, cliente e produto juntos
CREATE OR REPLACE VIEW vendas AS
SELECT
    o.order_id                       AS pedido_id,
    i.order_item_id                  AS item_numero,
    CASE o.order_status
        WHEN 'delivered'   THEN 'entregue'
        WHEN 'shipped'     THEN 'enviado'
        WHEN 'canceled'    THEN 'cancelado'
        WHEN 'unavailable' THEN 'indisponível'
        WHEN 'invoiced'    THEN 'faturado'
        WHEN 'processing'  THEN 'em processamento'
        WHEN 'created'     THEN 'criado'
        WHEN 'approved'    THEN 'aprovado'
        ELSE o.order_status
    END                              AS status_pedido,
    o.order_purchase_timestamp       AS data_compra,
    o.order_delivered_customer_date  AS data_entrega,
    o.order_estimated_delivery_date  AS data_entrega_prevista,
    EXTRACT(DAY FROM o.order_delivered_customer_date - o.order_purchase_timestamp)::INTEGER AS dias_entrega,
    o.order_delivered_customer_date > o.order_estimated_delivery_date AS atrasado,
    c.customer_unique_id             AS cliente_id,
    c.customer_city                  AS cidade,
    c.customer_state                 AS estado,
    COALESCE(REPLACE(p.product_category_name, '_', ' '), 'sem categoria') AS categoria,
    i.price                          AS preco,
    i.freight_value                  AS frete,
    i.price + i.freight_value        AS valor_total
FROM order_items i
JOIN orders o    ON o.order_id = i.order_id
JOIN customers c ON c.customer_id = o.customer_id
JOIN products p  ON p.product_id = i.product_id;
