from .semantic_analyzer import SemanticAnalyzer
import os
import shutil
import time


def create_test_files():
    """创建测试文件"""
    print("📁 创建测试文件...")

    os.makedirs('src', exist_ok=True)
    os.makedirs('src/utils', exist_ok=True)

    # 创建主测试文件
    with open('src/example.py', 'w', encoding='utf-8') as f:
        f.write('''def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

def calculate_product(x, y):
    result = x * y
    return result

def old_function():
    print("This function will be removed")
''')

    # 创建工具文件
    with open('src/utils/math_utils.py', 'w', encoding='utf-8') as f:
        f.write('''def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
''')

    with open('src/utils/string_utils.py', 'w', encoding='utf-8') as f:
        f.write('''def capitalize_string(s):
    return s.upper()

def reverse_string(s):
    return s[::-1]
''')

    print("✅ 测试文件创建完成")


def test_per_function_processing():
    """测试逐个函数处理的功能"""
    print("\n" + "=" * 60)
    print("测试: 逐个函数处理功能")
    print("=" * 60)

    # 重新创建干净的测试环境
    if os.path.exists('src'):
        shutil.rmtree('src')
    if os.path.exists('chroma_db'):
        shutil.rmtree('chroma_db')

    create_test_files()

    analyzer = SemanticAnalyzer(
        source_directories=['./src'],
        model_name="microsoft/codebert-base"
    )

    # 初始重建
    print("执行初始数据库重建...")
    analyzer.rebuild_database()
    initial_count = analyzer.get_database_info().get('function_count', 0)
    print(f"✅ 初始函数数量: {initial_count}")

    # 测试包含多个函数变更的git diff
    print("\n--- 测试多个函数变更 ---")
    complex_diff = '''diff --git a/src/example.py b/src/example.py
index 1234567..89abcde 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,8 +1,15 @@
 def calculate_sum(a, b):
-    """计算两个数的和"""
+    """计算两个数的和（增强版）"""
+    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
+        raise ValueError("输入必须是数字")
     return a + b

 def calculate_product(x, y):
-    result = x * y
-    return result
+    return x * y  # 简化实现
+
+def new_utility_function():
+    """新增的工具函数"""
+    return "utility result"

 def old_function():
     print("This function will be removed")
+    # 这个函数将被保留但修改了实现
diff --git a/src/utils/math_utils.py b/src/utils/math_utils.py
index 1234567..0000000
--- a/src/utils/math_utils.py
+++ /dev/null
@@ -1,8 +0,0 @@
-def multiply(a, b):
-    return a * b
-
-def divide(a, b):
-    if b == 0:
-        raise ValueError("Cannot divide by zero")
-    return a / b
'''

    print("执行逐个函数分析...")
    start_time = time.time()
    result = analyzer.analyze(complex_diff)
    processing_time = time.time() - start_time

    print(f"\n📊 分析结果:")
    print(f"  - 分析类型: {result.analysis_type}")
    print(f"  - 总耗时: {processing_time:.2f}s")
    print(f"  - 处理函数数: {len(result.changed_functions)}")
    print(f"  - 删除函数数: {result.deleted_functions_count}")
    print(f"  - 找到相似函数: {len(result.similar_functions)}")

    # 显示处理的函数详情
    print(f"\n🔍 处理的函数详情:")
    for i, func in enumerate(result.changed_functions):
        print(f"  {i + 1}. {func.name} (来自: {func.file_path})")

    # 显示相似性分析结果
    print(f"\n⭐ 相似性分析结果:")
    unique_similarities = {}
    for similar in result.similar_functions:
        key = f"{similar.function.name}->{similar.function.name}"
        if key not in unique_similarities or similar.similarity_score > unique_similarities[key]:
            unique_similarities[key] = similar.similarity_score

    for i, (key, score) in enumerate(list(unique_similarities.items())[:5]):
        source, target = key.split('->')
        print(f"  {i + 1}. {source} -> {target} (相似度: {score:.3f})")

    # 验证数据库状态
    final_count = analyzer.get_database_info().get('function_count', 0)
    print(f"\n📈 数据库统计:")
    print(f"  - 初始函数数: {initial_count}")
    print(f"  - 最终函数数: {final_count}")
    print(f"  - 净变化: {final_count - initial_count}")


def run_per_function_test():
    """运行逐个函数处理测试"""
    print("🚀 开始逐个函数处理测试")
    print("本测试将验证:")
    print("1. 逐个函数检索相似性")
    print("2. 批量更新数据库")
    print("3. 混合增删改操作处理")
    print()

    try:
        test_per_function_processing()

        print("\n" + "=" * 60)
        print("🎉 逐个函数处理测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理
        if os.path.exists('src'):
            shutil.rmtree('src')
        if os.path.exists('chroma_db'):
            shutil.rmtree('chroma_db')
        print("✅ 测试环境清理完成")



def run_per_function_test():
    """运行逐个函数处理测试"""
    print("🚀 开始逐个函数处理测试")
    print("本测试将验证:")
    print("1. 逐个函数检索相似性")
    print("2. 批量更新数据库")
    print("3. 混合增删改操作处理")
    print()

    analyzer = None

    try:
        test_per_function_processing()

        print("\n" + "=" * 60)
        print("🎉 逐个函数处理测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()




# 在 test_per_function_processing 函数中返回 analyzer
def test_per_function_processing():
    """测试逐个函数处理的功能"""
    print("\n" + "=" * 60)
    print("测试: 逐个函数处理功能")
    print("=" * 60)

    # 重新创建干净的测试环境
    if os.path.exists('src'):
        shutil.rmtree('src')
    if os.path.exists('chroma_db'):
        shutil.rmtree('chroma_db')

    create_test_files()

    analyzer = SemanticAnalyzer(
        source_directories=['./src'],
        model_name="microsoft/codebert-base"
    )

    # 初始重建
    print("执行初始数据库重建...")
    analyzer.rebuild_database()
    initial_count = analyzer.get_database_info().get('function_count', 0)
    print(f"✅ 初始函数数量: {initial_count}")

    # 测试包含多个函数变更的git diff
    print("\n--- 测试多个函数变更 ---")
    complex_diff = '''diff --git a/src/example.py b/src/example.py
index 1234567..89abcde 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,8 +1,15 @@
 def calculate_sum(a, b):
-    """计算两个数的和"""
+    """计算两个数的和（增强版）"""
+    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
+        raise ValueError("输入必须是数字")
     return a + b

 def calculate_product(x, y):
-    result = x * y
-    return result
+    return x * y  # 简化实现
+
+def new_utility_function():
+    """新增的工具函数"""
+    return "utility result"

 def old_function():
     print("This function will be removed")
+    # 这个函数将被保留但修改了实现
diff --git a/src/utils/math_utils.py b/src/utils/math_utils.py
index 1234567..0000000
--- a/src/utils/math_utils.py
+++ /dev/null
@@ -1,8 +0,0 @@
-def multiply(a, b):
-    return a * b
-
-def divide(a, b):
-    if b == 0:
-        raise ValueError("Cannot divide by zero")
-    return a / b
'''

    print("执行逐个函数分析...")
    start_time = time.time()
    result = analyzer.analyze(complex_diff)
    processing_time = time.time() - start_time
    print(result)
    print(f"\n📊 分析结果:")
    print(f"  - 分析类型: {result.analysis_type}")
    print(f"  - 总耗时: {processing_time:.2f}s")
    print(f"  - 处理函数数: {len(result.changed_functions)}")
    print(f"  - 删除函数数: {result.deleted_functions_count}")
    print(f"  - 找到相似函数: {len(result.similar_functions)}")

    # 显示处理的函数详情
    print(f"\n🔍 处理的函数详情:")
    for i, func in enumerate(result.changed_functions):
        print(f"  {i + 1}. {func.name} (来自: {func.file_path})")

    # 显示相似性分析结果
    print(f"\n⭐ 相似性分析结果:")
    unique_similarities = {}
    for similar in result.similar_functions:
        key = f"{similar.function.name}"
        if key not in unique_similarities or similar.similarity_score > unique_similarities[key]:
            unique_similarities[key] = similar.similarity_score

    for i, (func_name, score) in enumerate(list(unique_similarities.items())[:5]):
        print(f"  {i + 1}. {func_name} (最高相似度: {score:.3f})")

    # 验证数据库状态
    final_count = analyzer.get_database_info().get('function_count', 0)
    print(f"\n📈 数据库统计:")
    print(f"  - 初始函数数: {initial_count}")
    print(f"  - 最终函数数: {final_count}")
    print(f"  - 净变化: {final_count - initial_count}")

    return analyzer  # 返回analyzer用于后续清理


if __name__ == "__main__":
    run_per_function_test()
