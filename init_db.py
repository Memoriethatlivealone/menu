"""Safely initialize the local menu schema and optional demonstration dishes.

Run from the repository root: python init_db.py
Existing menu items and reservations are never deleted or replaced.
"""
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect, text

load_dotenv(Path(__file__).resolve().parent / ".env")
from agent.langchain_assistant import mysql_connection


MENU_TABLE = """
CREATE TABLE IF NOT EXISTS menu_items (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    dish_name VARCHAR(100) NOT NULL,
    price DECIMAL(8, 2) NOT NULL,
    description TEXT NULL,
    category VARCHAR(50) NOT NULL,
    spice_level TINYINT DEFAULT 0,
    flavor VARCHAR(100) NULL,
    main_ingredients TEXT NULL,
    cooking_method VARCHAR(50) NULL,
    is_vegetarian TINYINT(1) DEFAULT 0,
    allergens VARCHAR(200) NULL,
    is_available TINYINT(1) DEFAULT 1,
    is_featured TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

RESERVATION_TABLE = """
CREATE TABLE IF NOT EXISTS reservation_order (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    num_people INT NOT NULL,
    num_children INT NOT NULL,
    arrival_time DATETIME NOT NULL,
    seat_preference VARCHAR(100) NULL,
    main_dish_preference VARCHAR(100) NULL,
    other_comments TEXT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DEMO_DISHES = (
    ("演示菜品·清蒸鲈鱼", 68.00, "演示数据：清淡口味，仅用于测试点餐页面。", "主菜", 0, "清淡", "鲈鱼", "清蒸", 0, "鱼", 1, 1),
    ("演示菜品·宫保鸡丁", 38.00, "演示数据：微辣口味，仅用于测试点餐页面。", "主菜", 1, "咸香", "鸡肉、花生", "炒", 0, "花生", 1, 1),
    ("演示菜品·清炒时蔬", 26.00, "演示数据：素食菜品，仅用于测试点餐页面。", "蔬菜", 0, "清淡", "时令蔬菜", "清炒", 1, "", 1, 0),
)


def initialize_database(engine):
    with engine.begin() as conn:
        conn.execute(text(MENU_TABLE))
        conn.execute(text(RESERVATION_TABLE))

    columns = {column["name"] for column in inspect(engine).get_columns("menu_items")}
    if "is_featured" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN is_featured TINYINT(1) NOT NULL DEFAULT 0"))

    # Only seed a completely empty menu, never modify existing dishes or reservations.
    with engine.begin() as conn:
        menu_count = conn.execute(text("SELECT COUNT(*) FROM menu_items")).scalar_one()
        if menu_count == 0:
            conn.execute(text("""
                INSERT INTO menu_items
                (dish_name, price, description, category, spice_level, flavor,
                 main_ingredients, cooking_method, is_vegetarian, allergens,
                 is_available, is_featured)
                VALUES
                (:dish_name, :price, :description, :category, :spice_level, :flavor,
                 :main_ingredients, :cooking_method, :is_vegetarian, :allergens,
                 :is_available, :is_featured)
            """), [dict(zip(("dish_name", "price", "description", "category", "spice_level",
                             "flavor", "main_ingredients", "cooking_method", "is_vegetarian",
                             "allergens", "is_available", "is_featured"), dish))
                   for dish in DEMO_DISHES])
        summary = conn.execute(text("""
            SELECT COUNT(*) AS total, COALESCE(SUM(is_available = 1), 0) AS available,
                   COALESCE(SUM(is_featured = 1), 0) AS featured FROM menu_items
        """)).mappings().one()
        reservations = conn.execute(text("SELECT COUNT(*) FROM reservation_order")).scalar_one()
    return dict(summary), reservations


if __name__ == "__main__":
    menu, reservations = initialize_database(mysql_connection())
    print(f"菜单: {menu['total']} 条, 可售: {menu['available']} 条, 特色: {menu['featured']} 条; 预订: {reservations} 条")
