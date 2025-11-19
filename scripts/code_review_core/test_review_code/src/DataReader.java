package com.example.dataprocess;

import java.util.ArrayList;
import java.util.List;

/**
 * 数据读取器：负责读取原始数据，是数据处理流程的第一步
 */
public class DataReader {

    /**
     * 读取原始数据（模拟从文件/数据库读取）
     * @return 原始字符串列表（每行数据为一个元素）
     */
    public List<String> readRawData() {
        // 模拟原始数据：格式为 "用户名,年龄,城市"
        List<String> rawData = new ArrayList<>();
        rawData.add("张三,25,北京");
        rawData.add("李四,32,上海");
        rawData.add("王五,28,广州");
        rawData.add("赵六,40,深圳");
        rawData.add("无效数据,abc,"); // 包含需要清洗的无效数据

        System.out.println("✅ 成功读取原始数据，共 " + rawData.size() + " 条");
        return rawData;
    }

    // 测试入口
    public static void main(String[] args) {
        DataReader reader = new DataReader();
        reader.readRawData();
    }
}