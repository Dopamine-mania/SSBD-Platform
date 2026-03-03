#!/bin/bash

# 声匠录音棚排班与计费桌面平台 - 统一测试脚本
# 执行所有单元测试和 API 测试，输出明细和汇总

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  声匠录音棚 - 统一测试执行脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 pytest 是否安装
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest 未安装${NC}"
    echo "请运行: pip install pytest pytest-cov"
    exit 1
fi

# 初始化计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ========================================
# 1. 单元测试
# ========================================
echo -e "${YELLOW}[1/2] 执行单元测试...${NC}"
echo ""

if [ -d "unit_tests" ]; then
    pytest unit_tests/ -v --tb=short > /tmp/unit_test_output.txt 2>&1 || true

    # 解析结果
    UNIT_PASSED=$(grep -oP '\d+(?= passed)' /tmp/unit_test_output.txt || echo "0")
    UNIT_FAILED=$(grep -oP '\d+(?= failed)' /tmp/unit_test_output.txt || echo "0")

    TOTAL_TESTS=$((TOTAL_TESTS + UNIT_PASSED + UNIT_FAILED))
    PASSED_TESTS=$((PASSED_TESTS + UNIT_PASSED))
    FAILED_TESTS=$((FAILED_TESTS + UNIT_FAILED))

    echo -e "${GREEN}✓ 单元测试完成: ${UNIT_PASSED} 通过, ${UNIT_FAILED} 失败${NC}"

    # 显示详细输出
    if [ "$UNIT_FAILED" -gt 0 ]; then
        echo -e "${RED}失败详情:${NC}"
        grep -A 5 "FAILED" /tmp/unit_test_output.txt || true
    fi
else
    echo -e "${RED}✗ unit_tests/ 目录不存在${NC}"
    exit 1
fi

echo ""

# ========================================
# 2. API 测试
# ========================================
echo -e "${YELLOW}[2/2] 执行 API 测试...${NC}"
echo ""

if [ -d "API_tests" ] && [ "$(ls -A API_tests/*.py 2>/dev/null)" ]; then
    pytest API_tests/ -v --tb=short > /tmp/api_test_output.txt 2>&1 || true

    # 解析结果
    API_PASSED=$(grep -oP '\d+(?= passed)' /tmp/api_test_output.txt || echo "0")
    API_FAILED=$(grep -oP '\d+(?= failed)' /tmp/api_test_output.txt || echo "0")

    TOTAL_TESTS=$((TOTAL_TESTS + API_PASSED + API_FAILED))
    PASSED_TESTS=$((PASSED_TESTS + API_PASSED))
    FAILED_TESTS=$((FAILED_TESTS + API_FAILED))

    echo -e "${GREEN}✓ API 测试完成: ${API_PASSED} 通过, ${API_FAILED} 失败${NC}"

    # 显示详细输出
    if [ "$API_FAILED" -gt 0 ]; then
        echo -e "${RED}失败详情:${NC}"
        grep -A 5 "FAILED" /tmp/api_test_output.txt || true
    fi
else
    echo -e "${YELLOW}⚠ API_tests/ 目录为空或不存在，跳过 API 测试${NC}"
fi

echo ""

# ========================================
# 3. 测试汇总
# ========================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  测试汇总${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "总测试数: ${TOTAL_TESTS}"
echo -e "${GREEN}通过: ${PASSED_TESTS}${NC}"
echo -e "${RED}失败: ${FAILED_TESTS}${NC}"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ 存在失败测试，请检查上述详情${NC}"
    exit 1
fi
