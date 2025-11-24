import subprocess
import sys
import re
from datetime import datetime
import os

def run_tests_and_export():
    """Run all tests and export results to files"""
    
    print("🚀 RUNNING VALIDATION SUITE - EXPORTING TO FILES")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Run GAP 7 API tests
    print("1️⃣ Running GAP 7 API tests...")
    try:
        with open(f"gap7_results_{timestamp}.txt", "w", encoding="utf-8") as f:
            result = subprocess.run([
                sys.executable, '-X', 'utf8', 'test_api_endpoints.py', '-v'
            ], stdout=f, stderr=subprocess.STDOUT, timeout=180)
        
        print(f"✅ GAP 7 results exported to: gap7_results_{timestamp}.txt")
        gap7_file = f"gap7_results_{timestamp}.txt"
        
    except Exception as e:
        print(f"❌ GAP 7 test failed: {e}")
        gap7_file = None
    
    # 2. Run comprehensive tests
    print("2️⃣ Running comprehensive tests...")
    try:
        with open(f"comprehensive_results_{timestamp}.txt", "w", encoding="utf-8") as f:
            result = subprocess.run([
                sys.executable, '-X', 'utf8', 'test_tournament_comprehensive.py'
            ], stdout=f, stderr=subprocess.STDOUT, timeout=240)
        
        print(f"✅ Comprehensive results exported to: comprehensive_results_{timestamp}.txt")
        comp_file = f"comprehensive_results_{timestamp}.txt"
        
    except Exception as e:
        print(f"❌ Comprehensive test failed: {e}")
        comp_file = None
    
    # 3. Run scenario tests
    print("3️⃣ Running scenario tests...")
    try:
        with open(f"scenario_results_{timestamp}.txt", "w", encoding="utf-8") as f:
            result = subprocess.run([
                sys.executable, '-X', 'utf8', 'test_tournament_scenarios.py'
            ], stdout=f, stderr=subprocess.STDOUT, timeout=180)
        
        print(f"✅ Scenario results exported to: scenario_results_{timestamp}.txt")
        scenario_file = f"scenario_results_{timestamp}.txt"
        
    except Exception as e:
        print(f"❌ Scenario test failed: {e}")
        scenario_file = None
    
    # 4. Generate summary report
    print("4️⃣ Generating summary report...")
    
    summary_file = f"VALIDATION_SUMMARY_{timestamp}.md"
    
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"# Validation Suite Results\n\n")
        f.write(f"**Generated:** {datetime.now()}\n\n")
        f.write(f"## Files Generated\n\n")
        
        if gap7_file:
            f.write(f"- **GAP 7 API Tests:** `{gap7_file}`\n")
        if comp_file:
            f.write(f"- **Comprehensive Tests:** `{comp_file}`\n")
        if scenario_file:
            f.write(f"- **Scenario Tests:** `{scenario_file}`\n")
        
        f.write(f"\n## Analysis\n\n")
        f.write(f"Run the following to analyze results:\n\n")
        f.write(f"```python\n")
        f.write(f"# Analyze GAP 7 results\n")
        if gap7_file:
            f.write(f"analyze_gap7_results('{gap7_file}')\n")
        f.write(f"```\n\n")
        
        f.write(f"## Next Steps\n\n")
        f.write(f"1. Review the generated result files\n")
        f.write(f"2. Run analysis functions to interpret results\n")
        f.write(f"3. Determine if GAP 7 is closed (90%+ pass rate)\n")
        f.write(f"4. Check for regressions in existing functionality\n")
    
    print(f"📊 Summary report: {summary_file}")
    print("\n🎯 NEXT: Run analysis functions to interpret results")
    
    return gap7_file, comp_file, scenario_file, summary_file

def analyze_gap7_results(filename):
    """Analyze GAP 7 test results from file"""
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return
    
    print(f"📊 ANALYZING GAP 7 RESULTS: {filename}")
    print("=" * 50)
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse test results
    passed = len(re.findall(r'test_\d+.*?\.\.\..*?ok', content, re.IGNORECASE))
    failed = len(re.findall(r'test_\d+.*?\.\.\..*?FAIL', content, re.IGNORECASE))
    errors = len(re.findall(r'test_\d+.*?\.\.\..*?ERROR', content, re.IGNORECASE))
    
    # Alternative parsing
    if passed == 0 and failed == 0 and errors == 0:
        passed = content.count(' ... ok')
        failed = content.count(' ... FAIL')
        errors = content.count(' ... ERROR')
    
    total = passed + failed + errors
    
    print(f"📈 RESULTS:")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Errors: {errors} ⚠️")
    print(f"Total: {total}")
    
    if total > 0:
        pass_rate = (passed / total) * 100
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        # Compare to baseline (38%)
        baseline = 38.0
        improvement = pass_rate - baseline
        
        print(f"Baseline: {baseline}%")
        print(f"Improvement: {improvement:+.1f}%")
        
        if pass_rate >= 90:
            status = "✅ GAP 7 CLOSED"
        elif pass_rate >= 70:
            status = "⚠️ GAP 7 PARTIAL"
        elif improvement > 0:
            status = "📈 GAP 7 IMPROVING"
        else:
            status = "❌ GAP 7 OPEN"
    else:
        status = "❌ GAP 7 ERROR"
        pass_rate = 0
    
    print(f"Status: {status}")
    
    # Extract failed test names
    failed_tests = re.findall(r'(test_\d+[^.]*?)\.\.\..*?(?:FAIL|ERROR)', content, re.IGNORECASE)
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests[:10]:  # Show first 10
            print(f"  - {test}")
        if len(failed_tests) > 10:
            print(f"  ... and {len(failed_tests) - 10} more")
    
    return {
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'total': total,
        'pass_rate': pass_rate if total > 0 else 0,
        'status': status
    }

if __name__ == "__main__":
    # Run the validation suite
    gap7_file, comp_file, scenario_file, summary_file = run_tests_and_export()
    
    print("\n" + "=" * 60)
    print("🎯 TO ANALYZE RESULTS, RUN:")
    print("=" * 60)
    
    if gap7_file:
        print(f"analyze_gap7_results('{gap7_file}')")
    
    print(f"\nOr check the files manually:")
    if gap7_file:
        print(f"- {gap7_file}")
    if comp_file:
        print(f"- {comp_file}")
    if scenario_file:
        print(f"- {scenario_file}")
    print(f"- {summary_file}")