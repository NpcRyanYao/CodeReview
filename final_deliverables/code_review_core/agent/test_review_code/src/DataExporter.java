package com.example.dataprocess;

import java.util.List;

/**
 * 数据导出器：负责将处理后的有效数据导出，是数据处理流程的第三步
 */
public class DataExporter {

    /**
     * 导出处理后的数据（模拟导出到文件）
     * @param processedData 处理后的数据（来自DataProcessor）
     * @param exportPath 导出目标路径（模拟）
     * @return 导出是否成功
     */
    public boolean exportData(List<String> processedData, String exportPath) {
        // 校验输入参数
        if (processedData == null || processedData.isEmpty()) {
            System.out.println("❌ 无有效数据可导出");
            return false;
        }

        // 模拟导出逻辑：打印导出内容
        System.out.println("\n📤 开始导出数据到：" + exportPath);
        System.out.println("------------------------------");
        for (String data : processedData) {
            System.out.println(data); // 实际场景中会写入文件/数据库
        }
        System.out.println("------------------------------");
        System.out.println("✅ 数据导出成功，共导出 " + processedData.size() + " 条");

        return true;
    }

    // 测试入口（依赖DataReader和DataProcessor）
    public static void main(String[] args) {
        // 串联完整流程：读取→处理→导出
        DataReader reader = new DataReader();
        DataProcessor processor = new DataProcessor();
        DataExporter exporter = new DataExporter();

        List<String> rawData = reader.readRawData();
        List<String> processedData = processor.processData(rawData);
        exporter.exportData(processedData, "/data/processed/user_info.txt");
    }
}