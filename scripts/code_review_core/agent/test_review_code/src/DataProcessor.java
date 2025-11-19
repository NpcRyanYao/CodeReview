package com.example.dataprocess;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * 数据处理器：负责清洗和转换原始数据，是数据处理流程的第二步
 */
public class DataProcessor {

    /**
     * 处理原始数据：过滤无效数据 + 转换格式为"用户名-年龄-城市"
     * @param rawData 原始数据（来自DataReader）
     * @return 处理后的有效数据
     * @note 新增：1. 年龄范围过滤（20-35岁） 2. 按年龄升序排序
     */
    public List<String> processData(List<String> rawData) {
        List<String> processedData = new ArrayList<>();

        for (String data : rawData) {
            // 临时存储拆分后的字段，用于后续年龄校验和排序
            String username = "";
            int age = 0;
            String city = "";
            // 校验数据格式（必须包含3个字段，年龄为数字）
            String[] parts = data.split(",");
            if (parts.length == 3 && parts[1].matches("\\d+") && !parts[2].isEmpty()) {
                username = parts[0];
                age = Integer.parseInt(parts[1]);
                city = parts[2];

                // 新增：过滤年龄不在20-35岁范围内的数据
                if (age < 20 || age > 35) {
                    System.out.println("⚠️  过滤年龄超限数据：" + data + "（年龄限制：20-35岁）");
                    continue;
                }

                // 转换格式（保持原有格式不变）
                String formattedData = username + "-" + age + "-" + city;
                processedData.add(formattedData);
            } else {
                System.out.println("⚠️  过滤无效数据：" + data + "（格式错误/城市为空/年龄非数字）");
            }
        }

        // 新增：按年龄升序排序（拆分字符串获取年龄进行比较，增加格式容错）
        processedData.sort(Comparator.comparingInt(item -> {
            String[] parts = item.split("-");
            return parts.length >= 2 && parts[1].matches("\\d+") ? Integer.parseInt(parts[1]) : 0;
        }));

        // 优化日志：补充排序后的详细信息
        System.out.println("✅ 数据处理完成（已按年龄升序排序）");
        System.out.println("   - 原始数据总量：" + rawData.size() + " 条");
        System.out.println("   - 过滤后有效数据：" + processedData.size() + " 条");
        if (!processedData.isEmpty()) {
            String firstAge = processedData.get(0).split("-")[1];
            String lastAge = processedData.get(processedData.size() - 1).split("-")[1];
            System.out.println("   - 年龄范围：" + firstAge + "岁 - " + lastAge + "岁");
        }

        return processedData;
    }

    // 测试入口（依赖DataReader）
    public static void main(String[] args) {
        DataReader reader = new DataReader();
        DataProcessor processor = new DataProcessor();

        List<String> rawData = reader.readRawData();
        processor.processData(rawData);
    }
}