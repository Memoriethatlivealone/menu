SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
USE `menu`;
DROP TABLE IF EXISTS `menu_items`;
CREATE TABLE `menu_items`(
`id` int NOT NULL AUTO_INCREMENT COMMENT '菜品ID，主键自增',
`dish_name` varchar(100) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NOT NULL COMMENT '菜品名称',
`price` decimal(8, 2) NOT NULL COMMENT '价格（元）',
`description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
NULL COMMENT '菜品描述',
`category` varchar(50) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NOT NULL COMMENT '菜品分类',
`spice_level` tinyint NULL DEFAULT 0 COMMENT '辣度等级：0-不辣，1-微
辣，2-中辣，3-重辣',
`flavor` varchar(100) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '口味特点',
`main_ingredients` text CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NULL COMMENT '主要食材，多个食材用逗号分隔',
`cooking_method` varchar(50) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '烹饪方法',
`is_vegetarian` tinyint(1) NULL DEFAULT 0 COMMENT '是否素食：0-否，1-是
',
`allergens` varchar(200) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '过敏原信息，多个过敏原用逗号
分隔',
`is_available` tinyint(1) NULL DEFAULT 1 COMMENT '是否可供应：0-不可
用，1-可用',
`created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时
间',
`updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE
CURRENT_TIMESTAMP,
PRIMARY KEY (`id`) USING BTREE,
INDEX `idx_category`(`category`) USING BTREE,
INDEX `idx_is_available`(`is_available`) USING BTREE,
INDEX `idx_is_vegetarian`(`is_vegetarian`) USING BTREE,
INDEX `idx_price`(`price`) USING BTREE,
INDEX `idx_spice_level`(`spice_level`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE =
utf8mb4_unicode_ci COMMENT = '菜单表' ROW_FORMAT = Dynamic;
DROP TABLE IF EXISTS `reservation_order`;
CREATE TABLE `reservation_order` (
`id` int NOT NULL AUTO_INCREMENT COMMENT '预订单ID，主键自增',
`num_people` int NOT NULL COMMENT '客人人数',
`num_children` int NOT NULL COMMENT '儿童人数',
`arrival_time` datetime NOT NULL COMMENT '到达时间',
`seat_preference` varchar(100) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci DEFAULT NULL COMMENT '座位偏好',
`main_dish_preference` varchar(100) CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci DEFAULT NULL COMMENT '主菜偏好',
`other_comments` text CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci COMMENT '其他备注需求',
`created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时
间',
`updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE
CURRENT_TIMESTAMP COMMENT '更新时间',
PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
ROW_FORMAT=DYNAMIC COMMENT='预订单表'