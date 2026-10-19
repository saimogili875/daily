from models import db, Question, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

SEED_QUESTIONS = [
    {
        "title": "Reverse Words in a String",
        "difficulty": "easy",
        "topic": "Strings",
        "description": "Given a single line containing space-separated words, reverse the order of the words while keeping each word intact. Multiple consecutive spaces should be treated as a single space, and leading/trailing spaces should be removed.",
        "input_format": "A single line of text containing words separated by spaces.",
        "output_format": "Print the words in reverse order separated by a single space.",
        "constraints": "1 <= length of string <= 10^5",
        "samples": [
            {"input": "the sky is blue", "output": "blue is sky the", "explanation": "The words are reversed from last to first."},
            {"input": "  hello   world  ", "output": "world hello", "explanation": "Extra spaces are trimmed and collapsed to a single space."}
        ],
        "hidden_tests": [
            {"input": "python programming is fun", "output": "fun is programming python"},
            {"input": "singleword", "output": "singleword"},
            {"input": "a b c d e", "output": "e d c b a"},
            {"input": "   lots    of    spaces   here   ", "output": "here spaces of lots"},
            {"input": "123 456 789", "output": "789 456 123"}
        ],
        "hint": "Split by whitespace using str.split() without arguments and reverse the resulting list."
    },
    {
        "title": "Two Sum Target",
        "difficulty": "easy",
        "topic": "Arrays & Hashing",
        "description": "Given a target integer T followed by an array of space-separated integers on the next line, find if there exist two distinct indices whose elements sum up to T. Print 'YES' if such a pair exists, otherwise 'NO'.",
        "input_format": "First line: Target integer T.\nSecond line: Space-separated integers.",
        "output_format": "Print 'YES' or 'NO'.",
        "constraints": "-10^9 <= T <= 10^9\n2 <= length <= 10^5",
        "samples": [
            {"input": "9\n2 7 11 15", "output": "YES", "explanation": "2 + 7 = 9."},
            {"input": "10\n1 2 3 4", "output": "NO", "explanation": "No two numbers sum to 10."}
        ],
        "hidden_tests": [
            {"input": "0\n-5 2 5 8", "output": "YES"},
            {"input": "100\n50 50", "output": "YES"},
            {"input": "50\n50", "output": "NO"},
            {"input": "14\n1 3 5 7 9 11", "output": "YES"},
            {"input": "-10\n-20 10 -5 -5", "output": "YES"}
        ],
        "hint": "Use a hash set to store seen numbers and check for (T - num)."
    },
    {
        "title": "Valid Parentheses Check",
        "difficulty": "easy",
        "topic": "Stacks",
        "description": "Given a string containing only brackets '(', ')', '{', '}', '[' and ']', determine if the input string is valid. A bracket sequence is valid if open brackets are closed by the same type of brackets in the correct order.",
        "input_format": "A single line containing the bracket string.",
        "output_format": "Print 'VALID' if the string is balanced, otherwise print 'INVALID'.",
        "constraints": "1 <= length <= 10^5",
        "samples": [
            {"input": "()[]{}", "output": "VALID", "explanation": "All bracket pairs match properly."},
            {"input": "(]", "output": "INVALID", "explanation": "Mismatched bracket pair."}
        ],
        "hidden_tests": [
            {"input": "({[]})", "output": "VALID"},
            {"input": "([)]", "output": "INVALID"},
            {"input": "(((((", "output": "INVALID"},
            {"input": "()", "output": "VALID"},
            {"input": "}{", "output": "INVALID"}
        ],
        "hint": "Use a stack to push opening brackets and pop when a matching closing bracket is found."
    },
    {
        "title": "Fibonacci Number",
        "difficulty": "easy",
        "topic": "Dynamic Programming",
        "description": "Given a non-negative integer N, compute the N-th Fibonacci number where F(0) = 0, F(1) = 1, and F(N) = F(N-1) + F(N-2).",
        "input_format": "A single line containing an integer N.",
        "output_format": "Print the N-th Fibonacci number.",
        "constraints": "0 <= N <= 80",
        "samples": [
            {"input": "2", "output": "1", "explanation": "F(2) = F(1) + F(0) = 1 + 0 = 1."},
            {"input": "6", "output": "8", "explanation": "Sequence: 0, 1, 1, 2, 3, 5, 8."}
        ],
        "hidden_tests": [
            {"input": "0", "output": "0"},
            {"input": "1", "output": "1"},
            {"input": "10", "output": "55"},
            {"input": "20", "output": "6765"},
            {"input": "50", "output": "12586269025"}
        ],
        "hint": "Use iteration with two variables to avoid recursion stack overflow."
    },
    {
        "title": "Palindrome String",
        "difficulty": "easy",
        "topic": "Strings",
        "description": "Given a string, check if it reads the same backward as forward, ignoring casing and non-alphanumeric characters.",
        "input_format": "A single line of text.",
        "output_format": "Print 'TRUE' if it is a palindrome, otherwise 'FALSE'.",
        "constraints": "1 <= length <= 10^5",
        "samples": [
            {"input": "A man, a plan, a canal: Panama", "output": "TRUE", "explanation": "Ignoring non-alphanumeric characters gives 'amanaplanacanalpanama'."},
            {"input": "race a car", "output": "FALSE", "explanation": "'raceacar' is not a palindrome."}
        ],
        "hidden_tests": [
            {"input": "Was it a car or a cat I saw?", "output": "TRUE"},
            {"input": "No 'x' in Nixon", "output": "TRUE"},
            {"input": "hello", "output": "FALSE"},
            {"input": ".,!!", "output": "TRUE"},
            {"input": "0P", "output": "FALSE"}
        ],
        "hint": "Filter with char.isalnum() and lower(), then compare with reversed."
    },
    {
        "title": "Maximum Subarray Sum (Kadane's)",
        "difficulty": "medium",
        "topic": "Dynamic Programming",
        "description": "Given an array of integers, find the contiguous subarray (containing at least one number) which has the largest sum and print its sum.",
        "input_format": "First line: integer N. Second line: N space-separated integers.",
        "output_format": "Print the maximum subarray sum.",
        "constraints": "1 <= N <= 10^5\n-10^4 <= A[i] <= 10^4",
        "samples": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6", "explanation": "The subarray [4, -1, 2, 1] has the largest sum = 6."},
            {"input": "1\n1", "output": "1", "explanation": "Only one element."}
        ],
        "hidden_tests": [
            {"input": "5\n5 4 -1 7 8", "output": "23"},
            {"input": "4\n-5 -2 -8 -1", "output": "-1"},
            {"input": "6\n-1 2 3 -2 5 -1", "output": "8"},
            {"input": "3\n100 -50 200", "output": "250"},
            {"input": "2\n-10 10", "output": "10"}
        ],
        "hint": "Maintain current_sum and max_sum as you iterate through the list."
    },
    {
        "title": "Anagram Groups",
        "difficulty": "medium",
        "topic": "Hash Maps",
        "description": "Given a list of words on a single line separated by spaces, group the anagrams together. For each group, sort the words lexicographically. Print each group on a new line in sorted order of their first word.",
        "input_format": "A single line with space-separated words.",
        "output_format": "Each anagram group on a new line with words separated by a space.",
        "constraints": "1 <= total words <= 10^4",
        "samples": [
            {"input": "eat tea tan ate nat bat", "output": "ate eat tea\nbat\nnat tan", "explanation": "Words sharing same character counts are grouped and sorted."}
        ],
        "hidden_tests": [
            {"input": "a", "output": "a"},
            {"input": "cat dog act god tac", "output": "act cat tac\ndog god"},
            {"input": "silent listen enlist", "output": "enlist listen silent"},
            {"input": "abc bca cab cba bac acb", "output": "abc acb bac bca cab cba"},
            {"input": "hello world", "output": "hello\nworld"}
        ],
        "hint": "Use sorted word tuple as key in a dictionary grouping."
    },
    {
        "title": "Longest Common Prefix",
        "difficulty": "easy",
        "topic": "Strings",
        "description": "Write a program to find the longest common prefix string amongst an array of words. If there is no common prefix, print 'NONE'.",
        "input_format": "A single line with space-separated strings.",
        "output_format": "The longest common prefix, or 'NONE'.",
        "constraints": "1 <= number of words <= 1000",
        "samples": [
            {"input": "flower flow flight", "output": "fl", "explanation": "'fl' is common to all words."},
            {"input": "dog racecar car", "output": "NONE", "explanation": "No common prefix."}
        ],
        "hidden_tests": [
            {"input": "interspecies interstellar interstate", "output": "inters"},
            {"input": "apple", "output": "apple"},
            {"input": "throne throne", "output": "throne"},
            {"input": "prefix preview presentation", "output": "pre"},
            {"input": "a b c", "output": "NONE"}
        ],
        "hint": "Compare character by character across words up to the shortest word's length."
    },
    {
        "title": "Rotate Array by K Steps",
        "difficulty": "medium",
        "topic": "Arrays",
        "description": "Given an integer K followed by an array of space-separated integers on the next line, rotate the array to the right by K steps.",
        "input_format": "First line: integer K.\nSecond line: space-separated integers.",
        "output_format": "Space-separated integers after rotation.",
        "constraints": "0 <= K <= 10^9\n1 <= array length <= 10^5",
        "samples": [
            {"input": "3\n1 2 3 4 5 6 7", "output": "5 6 7 1 2 3 4", "explanation": "Rotate right by 3 positions."},
            {"input": "2\n-1 -100 3 99", "output": "3 99 -1 -100", "explanation": "Rotate right by 2 positions."}
        ],
        "hidden_tests": [
            {"input": "0\n1 2 3", "output": "1 2 3"},
            {"input": "4\n1 2 3 4", "output": "1 2 3 4"},
            {"input": "7\n1 2 3", "output": "3 1 2"},
            {"input": "1\n42", "output": "42"},
            {"input": "5\n10 20 30 40 50 60", "output": "20 30 40 50 60 10"}
        ],
        "hint": "Use slicing or reverse algorithm with K % length."
    },
    {
        "title": "Prime Number Sieve",
        "difficulty": "medium",
        "topic": "Math & Number Theory",
        "description": "Given an integer N, count how many prime numbers are strictly less than N.",
        "input_format": "A single line containing an integer N.",
        "output_format": "The count of prime numbers strictly less than N.",
        "constraints": "0 <= N <= 10^6",
        "samples": [
            {"input": "10", "output": "4", "explanation": "Primes less than 10 are 2, 3, 5, 7."},
            {"input": "0", "output": "0", "explanation": "No primes less than 0."}
        ],
        "hidden_tests": [
            {"input": "1", "output": "0"},
            {"input": "2", "output": "0"},
            {"input": "20", "output": "8"},
            {"input": "100", "output": "25"},
            {"input": "1000", "output": "168"}
        ],
        "hint": "Implement the Sieve of Eratosthenes with a boolean list."
    },
    {
        "title": "Merge Intervals",
        "difficulty": "medium",
        "topic": "Intervals & Sorting",
        "description": "Given N intervals with start and end times, merge all overlapping intervals and print the resulting non-overlapping intervals in ascending order.",
        "input_format": "First line: integer N.\nNext N lines: two space-separated integers representing start and end.",
        "output_format": "Each merged interval on a new line as 'start end'.",
        "constraints": "1 <= N <= 10^5",
        "samples": [
            {"input": "4\n1 3\n2 6\n8 10\n15 18", "output": "1 6\n8 10\n15 18", "explanation": "[1,3] and [2,6] overlap into [1,6]."},
            {"input": "2\n1 4\n4 5", "output": "1 5", "explanation": "Overlapping at boundary 4."}
        ],
        "hidden_tests": [
            {"input": "1\n1 5", "output": "1 5"},
            {"input": "3\n1 4\n0 2\n3 5", "output": "0 5"},
            {"input": "3\n1 2\n3 4\n5 6", "output": "1 2\n3 4\n5 6"},
            {"input": "4\n1 10\n2 3\n4 5\n6 7", "output": "1 10"},
            {"input": "2\n2 3\n1 4", "output": "1 4"}
        ],
        "hint": "Sort intervals by start time, then merge when current start <= previous end."
    },
    {
        "title": "Coin Change Minimum",
        "difficulty": "medium",
        "topic": "Dynamic Programming",
        "description": "Given an amount A on the first line and coin denominations on the second line (space-separated), find the fewest number of coins needed to make up that amount. If that amount cannot be made, print -1.",
        "input_format": "First line: integer Amount A.\nSecond line: space-separated coin denominations.",
        "output_format": "Minimum coins needed, or -1.",
        "constraints": "0 <= A <= 10^4\n1 <= coins count <= 100",
        "samples": [
            {"input": "11\n1 2 5", "output": "3", "explanation": "11 = 5 + 5 + 1 (3 coins)."},
            {"input": "3\n2", "output": "-1", "explanation": "Cannot make 3 with only coin 2."}
        ],
        "hidden_tests": [
            {"input": "0\n1", "output": "0"},
            {"input": "7\n2 4", "output": "-1"},
            {"input": "6249\n186 419 83 408", "output": "20"},
            {"input": "100\n1 5 10 25", "output": "4"},
            {"input": "1\n2", "output": "-1"}
        ],
        "hint": "DP array of size A+1 initialized to infinity, dp[0] = 0."
    },
    {
        "title": "Binary Search",
        "difficulty": "easy",
        "topic": "Binary Search",
        "description": "Given a target T on the first line and a sorted array of space-separated integers on the second line, find the 0-based index of T. If T does not exist, print -1.",
        "input_format": "First line: integer T.\nSecond line: space-separated sorted integers.",
        "output_format": "The 0-based index of T, or -1.",
        "constraints": "-10^9 <= T <= 10^9\n1 <= array size <= 10^5",
        "samples": [
            {"input": "9\n-1 0 3 5 9 12", "output": "4", "explanation": "9 exists at index 4."},
            {"input": "2\n-1 0 3 5 9 12", "output": "-1", "explanation": "2 does not exist."}
        ],
        "hidden_tests": [
            {"input": "5\n5", "output": "0"},
            {"input": "10\n1 2 3 4 5", "output": "-1"},
            {"input": "1\n1 3 5 7 9", "output": "0"},
            {"input": "9\n1 3 5 7 9", "output": "4"},
            {"input": "-5\n-10 -5 0 5 10", "output": "1"}
        ],
        "hint": "Use standard left/right pointer binary search."
    },
    {
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "medium",
        "topic": "Sliding Window",
        "description": "Given a string S, find the length of the longest substring without repeating characters.",
        "input_format": "A single line containing string S.",
        "output_format": "An integer representing the length.",
        "constraints": "0 <= length <= 5 * 10^4",
        "samples": [
            {"input": "abcabcbb", "output": "3", "explanation": "The answer is 'abc', with the length of 3."},
            {"input": "bbbbb", "output": "1", "explanation": "The answer is 'b', length 1."}
        ],
        "hidden_tests": [
            {"input": "pwwkew", "output": "3"},
            {"input": "", "output": "0"},
            {"input": "abcdefg", "output": "7"},
            {"input": "dvdf", "output": "3"},
            {"input": "tmmzuxt", "output": "5"}
        ],
        "hint": "Sliding window with a dictionary storing last seen index of each character."
    },
    {
        "title": "Climbing Stairs",
        "difficulty": "easy",
        "topic": "Dynamic Programming",
        "description": "You are climbing a staircase. It takes N steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
        "input_format": "A single integer N.",
        "output_format": "Number of distinct ways.",
        "constraints": "1 <= N <= 45",
        "samples": [
            {"input": "2", "output": "2", "explanation": "1 step + 1 step, or 2 steps."},
            {"input": "3", "output": "3", "explanation": "1+1+1, 1+2, 2+1."}
        ],
        "hidden_tests": [
            {"input": "1", "output": "1"},
            {"input": "4", "output": "5"},
            {"input": "5", "output": "8"},
            {"input": "10", "output": "89"},
            {"input": "35", "output": "14930352"}
        ],
        "hint": "Ways to step N is ways(N-1) + ways(N-2)."
    },
    {
        "title": "Top K Frequent Elements",
        "difficulty": "medium",
        "topic": "Heap & Hash Map",
        "description": "Given an integer K on the first line and an array of space-separated integers on the second line, print the K most frequent elements in descending order of frequency. If two elements have equal frequency, sort them in ascending order of their value.",
        "input_format": "First line: integer K.\nSecond line: space-separated integers.",
        "output_format": "K space-separated integers.",
        "constraints": "1 <= K <= number of unique elements <= 10^5",
        "samples": [
            {"input": "2\n1 1 1 2 2 3", "output": "1 2", "explanation": "1 occurs 3 times, 2 occurs 2 times."},
            {"input": "1\n1", "output": "1", "explanation": "Only one element."}
        ],
        "hidden_tests": [
            {"input": "2\n4 1 -1 2 -1 2 3", "output": "-1 2"},
            {"input": "3\n5 5 2 2 3 3 1", "output": "2 3 5"},
            {"input": "1\n10 20 30 10", "output": "10"},
            {"input": "4\n1 2 3 4", "output": "1 2 3 4"},
            {"input": "2\n9 9 9 8 8 7", "output": "9 8"}
        ],
        "hint": "Count frequencies using collections.Counter, then sort with key=(-freq, val)."
    },
    {
        "title": "Product of Array Except Self",
        "difficulty": "medium",
        "topic": "Prefix & Suffix",
        "description": "Given an integer array on a single line, return an array such that output[i] is equal to the product of all the elements of nums except nums[i]. Do it without using division.",
        "input_format": "Space-separated integers.",
        "output_format": "Space-separated integers representing the product array.",
        "constraints": "2 <= length <= 10^5\n-30 <= nums[i] <= 30",
        "samples": [
            {"input": "1 2 3 4", "output": "24 12 8 6", "explanation": "24=2*3*4, 12=1*3*4, 8=1*2*4, 6=1*2*3."},
            {"input": "-1 1 0 -3 3", "output": "0 0 9 0 0", "explanation": "Products around 0."}
        ],
        "hidden_tests": [
            {"input": "2 3", "output": "3 2"},
            {"input": "1 0", "output": "0 1"},
            {"input": "0 0", "output": "0 0"},
            {"input": "2 3 4 5", "output": "60 40 30 24"},
            {"input": "-2 4 -1 5", "output": "-20 10 -40 8"}
        ],
        "hint": "Construct prefix products array and suffix products array."
    },
    {
        "title": "Trapping Rain Water",
        "difficulty": "hard",
        "topic": "Two Pointers",
        "description": "Given N non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.",
        "input_format": "Space-separated non-negative integers representing elevation.",
        "output_format": "Single integer: total units of trapped rain water.",
        "constraints": "1 <= length <= 2 * 10^4\n0 <= height[i] <= 10^5",
        "samples": [
            {"input": "0 1 0 2 1 0 1 3 2 1 2 1", "output": "6", "explanation": "6 units of water are trapped."},
            {"input": "4 2 0 3 2 5", "output": "9", "explanation": "9 units of water are trapped."}
        ],
        "hidden_tests": [
            {"input": "1 2 3 4 5", "output": "0"},
            {"input": "5 4 3 2 1", "output": "0"},
            {"input": "3 0 2 0 4", "output": "7"},
            {"input": "2 0 2", "output": "2"},
            {"input": "5 1 2 1 5", "output": "11"}
        ],
        "hint": "Use two pointers from left and right maintaining left_max and right_max."
    },
    {
        "title": "Matrix Spiral Order",
        "difficulty": "medium",
        "topic": "2D Arrays",
        "description": "Given an M x N matrix, return all elements of the matrix in spiral order (clockwise starting from top-left).",
        "input_format": "First line: two integers M and N.\nNext M lines: N space-separated integers.",
        "output_format": "Space-separated elements in spiral traversal order.",
        "constraints": "1 <= M, N <= 100",
        "samples": [
            {"input": "3 3\n1 2 3\n4 5 6\n7 8 9", "output": "1 2 3 6 9 8 7 4 5", "explanation": "Clockwise traversal from 1 to 5."},
            {"input": "3 4\n1 2 3 4\n5 6 7 8\n9 10 11 12", "output": "1 2 3 4 8 12 11 10 9 5 6 7", "explanation": "Rectangular matrix traversal."}
        ],
        "hidden_tests": [
            {"input": "1 1\n42", "output": "42"},
            {"input": "1 4\n1 2 3 4", "output": "1 2 3 4"},
            {"input": "4 1\n1\n2\n3\n4", "output": "1 2 3 4"},
            {"input": "2 2\n1 2\n3 4", "output": "1 2 4 3"},
            {"input": "3 1\n10\n20\n30", "output": "10 20 30"}
        ],
        "hint": "Maintain boundaries top, bottom, left, right and move inward."
    },
    {
        "title": "Lowest Common Ancestor in BST",
        "difficulty": "medium",
        "topic": "Trees",
        "description": "Given a level-order representation of a Binary Search Tree where null nodes are represented by -1, and two values P and Q, find the value of their Lowest Common Ancestor (LCA).",
        "input_format": "First line: space-separated integers of BST in level order.\nSecond line: two integers P and Q.",
        "output_format": "The value of the LCA node.",
        "constraints": "Tree contains unique positive values. 2 <= number of nodes <= 10^4",
        "samples": [
            {"input": "6 2 8 0 4 7 9\n2 8", "output": "6", "explanation": "6 is the root and splits 2 and 8."},
            {"input": "6 2 8 0 4 7 9\n2 4", "output": "2", "explanation": "2 is ancestor of 4 and itself."}
        ],
        "hidden_tests": [
            {"input": "2 1 3\n1 3", "output": "2"},
            {"input": "5 3 6 2 4\n2 4", "output": "3"},
            {"input": "10 5 15 3 7\n3 7", "output": "5"},
            {"input": "20 10 30 5 15\n5 15", "output": "10"},
            {"input": "8 4 12 2 6 10 14\n10 14", "output": "12"}
        ],
        "hint": "In a BST, if both P and Q are smaller than current, go left; if both greater, go right."
    },
    {
        "title": "Evaluate Reverse Polish Notation",
        "difficulty": "medium",
        "topic": "Stacks",
        "description": "Evaluate the value of an arithmetic expression in Reverse Polish Notation (postfix). Valid operators are +, -, *, /. Division between two integers truncates toward zero.",
        "input_format": "Space-separated tokens of the RPN expression.",
        "output_format": "Single integer: result of evaluation.",
        "constraints": "1 <= tokens <= 10^4",
        "samples": [
            {"input": "2 1 + 3 *", "output": "9", "explanation": "((2 + 1) * 3) = 9."},
            {"input": "4 13 5 / +", "output": "6", "explanation": "(4 + (13 / 5)) = 6."}
        ],
        "hidden_tests": [
            {"input": "10 6 9 3 + -11 * / * 17 + 5 +", "output": "22"},
            {"input": "3", "output": "3"},
            {"input": "4 2 -", "output": "2"},
            {"input": "0 3 /", "output": "0"},
            {"input": "-5 5 +", "output": "0"}
        ],
        "hint": "Push numbers to stack. On operator, pop two operands and push result (truncate division using int(a / b))."
    },
    {
        "title": "Longest Increasing Subsequence",
        "difficulty": "medium",
        "topic": "Dynamic Programming",
        "description": "Given an integer array, return the length of the longest strictly increasing subsequence.",
        "input_format": "Space-separated integers.",
        "output_format": "Length of longest increasing subsequence.",
        "constraints": "1 <= length <= 2500",
        "samples": [
            {"input": "10 9 2 5 3 7 101 18", "output": "4", "explanation": "Longest increasing subsequence is [2, 3, 7, 101], length 4."},
            {"input": "0 1 0 3 2 3", "output": "4", "explanation": "Subsequence [0, 1, 2, 3], length 4."}
        ],
        "hidden_tests": [
            {"input": "7 7 7 7 7 7", "output": "1"},
            {"input": "1 3 6 7 9 4 10 5 6", "output": "6"},
            {"input": "5", "output": "1"},
            {"input": "3 2 1", "output": "1"},
            {"input": "1 2 3 4 5", "output": "5"}
        ],
        "hint": "Use patience sorting with bisect_left for O(N log N) time."
    },
    {
        "title": "Word Search in Grid",
        "difficulty": "medium",
        "topic": "Backtracking / DFS",
        "description": "Given an M x N grid of characters and a word, return 'FOUND' if the word exists in the grid, otherwise 'NOT FOUND'. The word can be constructed from letters of sequentially adjacent cells (horizontally or vertically neighboring). The same letter cell may not be used more than once.",
        "input_format": "First line: M N Word.\nNext M lines: N space-separated characters.",
        "output_format": "'FOUND' or 'NOT FOUND'.",
        "constraints": "1 <= M, N <= 6\n1 <= length of word <= 15",
        "samples": [
            {"input": "3 4 ABCCED\nA B C E\nS F C S\nA D E E", "output": "FOUND", "explanation": "Path A -> B -> C -> C -> E -> D exists."},
            {"input": "3 4 SEE\nA B C E\nS F C S\nA D E E", "output": "FOUND", "explanation": "Path S -> E -> E exists."}
        ],
        "hidden_tests": [
            {"input": "3 4 ABCE\nA B C E\nS F C S\nA D E E", "output": "FOUND"},
            {"input": "1 1 A\nA", "output": "FOUND"},
            {"input": "1 1 B\nA", "output": "NOT FOUND"},
            {"input": "2 2 ABCD\nA B\nC D", "output": "NOT FOUND"},
            {"input": "2 2 ACDB\nA B\nC D", "output": "FOUND"}
        ],
        "hint": "DFS from each cell matching word[0] with visited cell tracking."
    },
    {
        "title": "Count Inversions",
        "difficulty": "hard",
        "topic": "Divide and Conquer",
        "description": "Given an array of integers, count the number of inversions in the array. Two elements A[i] and A[j] form an inversion if A[i] > A[j] and i < j.",
        "input_format": "Space-separated integers.",
        "output_format": "Single integer: count of inversions.",
        "constraints": "1 <= N <= 10^5",
        "samples": [
            {"input": "2 4 1 3 5", "output": "3", "explanation": "Inversions are (2,1), (4,1), (4,3)."},
            {"input": "5 4 3 2 1", "output": "10", "explanation": "Reverse sorted array has maximum inversions."}
        ],
        "hidden_tests": [
            {"input": "1 2 3 4 5", "output": "0"},
            {"input": "1", "output": "0"},
            {"input": "8 4 2 1", "output": "6"},
            {"input": "3 1 2", "output": "2"},
            {"input": "10 20 30 5", "output": "3"}
        ],
        "hint": "Modify Merge Sort to count cross inversions during merge step."
    },
    {
        "title": "Median of Two Sorted Arrays",
        "difficulty": "hard",
        "topic": "Binary Search",
        "description": "Given two sorted arrays of integers, find the median of the two sorted arrays. Print the median rounded to 1 decimal place (e.g. 2.0 or 2.5).",
        "input_format": "First line: space-separated integers of array 1.\nSecond line: space-separated integers of array 2.",
        "output_format": "The median value formatted to 1 decimal place.",
        "constraints": "Total elements between 1 and 2 * 10^5",
        "samples": [
            {"input": "1 3\n2", "output": "2.0", "explanation": "Merged is [1, 2, 3], median is 2.0."},
            {"input": "1 2\n3 4", "output": "2.5", "explanation": "Merged is [1, 2, 3, 4], median is (2+3)/2 = 2.5."}
        ],
        "hidden_tests": [
            {"input": "0 0\n0 0", "output": "0.0"},
            {"input": "10\n", "output": "10.0"},
            {"input": "1 5 9\n2 6 10", "output": "5.5"},
            {"input": "1 2\n3 4 5 6", "output": "3.5"},
            {"input": "100\n200", "output": "150.0"}
        ],
        "hint": "Partition both arrays such that left halves equal right halves."
    },
    {
        "title": "Edit Distance (Levenshtein)",
        "difficulty": "hard",
        "topic": "Dynamic Programming",
        "description": "Given two strings word1 and word2, return the minimum number of operations required to convert word1 to word2. You have three permitted operations: Insert a character, Delete a character, Replace a character.",
        "input_format": "First line: word1.\nSecond line: word2.",
        "output_format": "Single integer: minimum edit distance.",
        "constraints": "0 <= length <= 500",
        "samples": [
            {"input": "horse\nros", "output": "3", "explanation": "horse -> rorse -> rose -> ros."},
            {"input": "intention\nexecution", "output": "5", "explanation": "5 operations required."}
        ],
        "hidden_tests": [
            {"input": "a\na", "output": "0"},
            {"input": "sea\neat", "output": "2"},
            {"input": "kitten\nsitting", "output": "3"},
            {"input": "algorithm\naltistic", "output": "6"},
            {"input": "abc\ndef", "output": "3"}
        ],
        "hint": "Classic 2D DP table: dp[i][j] = 1 + min(insert, delete, replace)."
    },
    {
        "title": "Find the Duplicate Number",
        "difficulty": "medium",
        "topic": "Floyd Cycle Detection",
        "description": "Given an array of integers nums containing N + 1 integers where each integer is between 1 and N (inclusive), prove that at least one duplicate number must exist. Find and print this duplicate number without modifying the array.",
        "input_format": "Space-separated integers.",
        "output_format": "The duplicate number.",
        "constraints": "2 <= length <= 10^5",
        "samples": [
            {"input": "1 3 4 2 2", "output": "2", "explanation": "2 appears twice."},
            {"input": "3 1 3 4 2", "output": "3", "explanation": "3 appears twice."}
        ],
        "hidden_tests": [
            {"input": "1 1", "output": "1"},
            {"input": "1 1 2", "output": "1"},
            {"input": "2 5 9 6 9 3 8 9 7 1", "output": "9"},
            {"input": "3 3 3 3 3", "output": "3"},
            {"input": "4 3 1 2 4", "output": "4"}
        ],
        "hint": "Use Floyd's Tortoise and Hare cycle detection on the array values as indices."
    },
    {
        "title": "Subarray Sum Equals K",
        "difficulty": "medium",
        "topic": "Prefix Sums & Hash Map",
        "description": "Given an integer K on the first line and an array of space-separated integers on the second line, find the total number of continuous subarrays whose sum equals to K.",
        "input_format": "First line: integer K.\nSecond line: space-separated integers.",
        "output_format": "Total count of subarrays with sum equal to K.",
        "constraints": "1 <= length <= 2 * 10^4\n-1000 <= nums[i] <= 1000",
        "samples": [
            {"input": "2\n1 1 1", "output": "2", "explanation": "[1,1] from indices 0..1 and 1..2."},
            {"input": "3\n1 2 3", "output": "2", "explanation": "[1,2] and [3]."}
        ],
        "hidden_tests": [
            {"input": "0\n1 -1 0", "output": "3"},
            {"input": "7\n3 4 7 2 -3 1 4 2", "output": "4"},
            {"input": "5\n5", "output": "1"},
            {"input": "10\n1 2 3", "output": "0"},
            {"input": "-2\n-1 -1 1", "output": "1"}
        ],
        "hint": "Track running prefix sums in a hash map: count += prefix_count[curr_sum - K]."
    },
    {
        "title": "Kth Largest Element in an Array",
        "difficulty": "medium",
        "topic": "Heap / Quickselect",
        "description": "Given an integer K on the first line and an array of space-separated integers on the second line, return the K-th largest element in the array.",
        "input_format": "First line: integer K.\nSecond line: space-separated integers.",
        "output_format": "The K-th largest element.",
        "constraints": "1 <= K <= length <= 10^5",
        "samples": [
            {"input": "2\n3 2 1 5 6 4", "output": "5", "explanation": "Sorted descending: 6, 5, 4, 3, 2, 1. 2nd largest is 5."},
            {"input": "4\n3 2 3 1 2 4 5 5 6", "output": "4", "explanation": "4th largest is 4."}
        ],
        "hidden_tests": [
            {"input": "1\n10 20 30", "output": "30"},
            {"input": "3\n7 10 4 3 20 15", "output": "10"},
            {"input": "1\n-5", "output": "-5"},
            {"input": "5\n5 4 3 2 1", "output": "1"},
            {"input": "2\n99 99 98", "output": "99"}
        ],
        "hint": "Use a min-heap of size K or heapq.nlargest."
    },
    {
        "title": "Rotten Oranges",
        "difficulty": "medium",
        "topic": "BFS",
        "description": "You are given an M x N grid where each cell has values: 0 (empty), 1 (fresh orange), 2 (rotten orange). Every minute, any fresh orange that is 4-directionally adjacent to a rotten orange becomes rotten. Return the minimum number of minutes that must elapse until no cell has a fresh orange. If this is impossible, return -1.",
        "input_format": "First line: two integers M and N.\nNext M lines: N space-separated integers (0, 1, or 2).",
        "output_format": "Minimum minutes, or -1.",
        "constraints": "1 <= M, N <= 50",
        "samples": [
            {"input": "3 3\n2 1 1\n1 1 0\n0 1 1", "output": "4", "explanation": "Takes 4 minutes for all oranges to rot."},
            {"input": "3 3\n2 1 1\n0 1 1\n1 0 1", "output": "-1", "explanation": "Bottom-left orange cannot be reached."}
        ],
        "hidden_tests": [
            {"input": "1 2\n0 2", "output": "0"},
            {"input": "1 1\n1", "output": "-1"},
            {"input": "1 1\n2", "output": "0"},
            {"input": "2 2\n2 1\n1 1", "output": "2"},
            {"input": "3 3\n0 2 0\n0 1 0\n0 1 0", "output": "2"}
        ],
        "hint": "Multi-source BFS starting with all initially rotten oranges in a queue."
    }
]


def seed_database(app):
    """Populates the database with initial admin and 30 Python questions."""
    with app.app_context():
        db.create_all()

        # Seed initial admin if not present
        admin_username = app.config.get('INITIAL_ADMIN_USERNAME', 'admin')
        admin_email = app.config.get('INITIAL_ADMIN_EMAIL', 'admin@dailycodeexam.com')
        admin_password = app.config.get('INITIAL_ADMIN_PASSWORD', 'AdminSecurePass!2026#')

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
            admin = User(
                username=admin_username,
                email=admin_email,
                password_hash=hashed_pw,
                is_admin=True
            )
            db.session.add(admin)
            print(f"[Seed] Created initial admin: {admin_username}")

        # Check existing questions
        existing_count = Question.query.count()
        if existing_count < len(SEED_QUESTIONS):
            added = 0
            for q_data in SEED_QUESTIONS:
                # Check by title
                exists = Question.query.filter_by(title=q_data['title']).first()
                if not exists:
                    q = Question(
                        title=q_data['title'],
                        difficulty=q_data['difficulty'],
                        topic=q_data['topic'],
                        description=q_data['description'],
                        input_format=q_data['input_format'],
                        output_format=q_data['output_format'],
                        constraints=q_data['constraints'],
                        hint=q_data.get('hint', ''),
                        time_limit_sec=q_data.get('time_limit_sec', 5),
                        is_ai_generated=False,
                        numpy_allowed=q_data.get('numpy_allowed', False)
                    )
                    q.samples = q_data['samples']
                    q.hidden_tests = q_data['hidden_tests']
                    db.session.add(q)
                    added += 1

            db.session.commit()
            print(f"[Seed] Added {added} seeded coding questions (Total: {Question.query.count()}).")
        else:
            print(f"[Seed] Database already contains {existing_count} questions.")
