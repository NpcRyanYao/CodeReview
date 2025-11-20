import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 数据预处理工具类
 * 包含：缺失值处理、异常值检测、数据转换、格式标准化、数据过滤等功能
 */
public class DataPreprocessor {
    // 日期格式常量
    public static final String DATE_FORMAT_DEFAULT = "yyyy-MM-dd";
    public static final String DATE_FORMAT_TIMESTAMP = "yyyy-MM-dd HH:mm:ss";

    // 数值处理默认参数
    private static final int DEFAULT_SCALE = 2; // 小数默认保留位数
    private static final double DEFAULT_FILL_VALUE = 0.0; // 默认填充值
    private static final double OUTLIER_STD_MULTIPLE = 3.0; // 异常值检测-标准差倍数（3σ原则）

    // ==================== 缺失值处理 ====================

    /**
     * 处理数值型集合的缺失值（null或NaN）
     *
     * @param data     原始数据集合
     * @param strategy 处理策略：FILL_DEFAULT(填充默认值)、FILL_MEAN(填充均值)、FILL_MEDIAN(填充中位数)、REMOVE(移除)
     * @return 处理后的数据
     */
    public static List<Double> handleMissingValues(List<Double> data, MissingValueStrategy strategy) {
        if (data == null || data.isEmpty()) {
            return new ArrayList<>();
        }

        // 过滤非空数据
        List<Double> validData = data.stream()
                .filter(Objects::nonNull)
                .filter(d -> !Double.isNaN(d))
                .collect(Collectors.toList());

        if (validData.isEmpty()) {
            return new ArrayList<>();
        }

        double fillValue = DEFAULT_FILL_VALUE;
        switch (strategy) {
            case FILL_MEAN:
                fillValue = calculateMean(validData);
                break;
            case FILL_MEDIAN:
                fillValue = calculateMedian(validData);
                break;
            case REMOVE:
                return validData;
            case FILL_DEFAULT:
            default:
                break;
        }

        // 填充缺失值
        return data.stream()
                .map(d -> (d == null || Double.isNaN(d)) ? fillValue : d)
                .collect(Collectors.toList());
    }
}