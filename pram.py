# SPDX-License-Identifier: MIT
import pandas as pd
import numpy as np
import argparse
import os
from collections import Counter
import logging

class Pram:

    @staticmethod
    def __get_transition_matrix__(values):
        """
        Create a standard transition matrix
        :param values:
        :return:
        """
        # Create a raw transition matrix

        # Generate the product of the values
        left, right = pd.core.reshape.util.cartesian_product([values, values])
        pairs = pd.DataFrame(dict(Source=left, Target=right)).values

        # Create a transition matrix using the counts of A:B
        matrix = pd.Series(Counter(map(tuple, pairs))).unstack().fillna(0)

        # Normalize the columns to sum to 1
        matrix = matrix.divide(matrix.sum(axis=0), axis=1)

        return matrix

    @staticmethod
    def __get_weighted_transition_matrix__(values, m, alpha):
        """
        Create a transition matrix weighted by alpha
        :param values:
        :param alpha:
        :param m:
        :return:
        """
        tm = Pram.__get_transition_matrix__(values)

        # Apply minimum value to diagonal using m
        diag = np.diag(tm)
        diag = [m if a_ < m else a_ for a_ in diag]
        diag = pd.Series(diag, index=tm.columns)
        np.fill_diagonal(tm.values, diag)

        # normalise so cols add up to 1
        tm = tm.div(tm.sum(axis=0), axis=1)

        # identity matrix of diagonal
        ei = tm.copy()
        for col in ei.columns:
            ei[col].values[:] = 0
        np.fill_diagonal(ei.values, 1)

        # apply alpha
        wm = alpha * tm + (1 - alpha) * ei

        # normalise so cols add up to 1
        wm = wm.div(wm.sum(axis=0), axis=1)

        return wm

    @staticmethod
    def __pram_replace__(tm, current_value):
        """
        Randomly changes values using the supplied transition matrix
        :param tm:
        :param current_value:
        :return:
        """
        column = tm[current_value]
        return np.random.choice(column.index, p=column.values)

    @staticmethod
    def pram(data, m=0.8, alpha=0.5, columns=None):
        """
        Uses PRAM to add perturbation to the supplied dataset
        :param data: a dataframe
        :param m: min diagonal value (defaults to 0.8)
        :param alpha: the degree of change, from 0 (no changes) to 1 (max changes). Defaults to 0.5
        :param columns: a list of the names of the columns to apply PRAM to. Defaults to None, applying to all columns.
        :return:
        """

        # Convert everything in the dataframe into a string - we can only
        # work with factors/tokens using PRAM
        data = data.applymap(str)

        # Create the weighted transition matrix for each column
        tm = {}

        if not columns:
            columns = data.columns

        for column in columns:
            tm[column] = Pram.__get_weighted_transition_matrix__(data[column].values, m, alpha)

        # For each row apply PRAM
        for index, row in data.iterrows():
            for column in data.columns:
                row[column] = Pram.__pram_replace__(tm[column], row[column])

        return data

    @staticmethod
    def __print_frequencies__(input_df, output_df):
        """
        Prints a table of the frequencies of values for the input and the output,
        enabling the user to determine whether the PRAM algorithm has substantially
        altered the 'shape' of the data and needs to modify the threshold and/or
        alpha.
        :param input_df: the original dataframe
        :param output_df: the modified dataframe
        :return: None. Outputs the table to STDOUT
        """
        input_df = input_df.applymap(str)
        freq = None
        for column in input_df.columns:
            i = input_df[column]
            o = output_df[column]
            ip = i.value_counts(normalize=True).round(2)
            op = o.value_counts(normalize=True).round(2)
            p = pd.DataFrame({'Column': column, 'Original': ip, "Output": op}).fillna(0)
            if freq is None:
                freq = p
            else:
                freq = pd.concat([freq, p])
        print(freq)


def pram(data, m=0.8, alpha=0.5, columns=None):
    """
    Uses PRAM to add perturbation to the supplied dataset
    :param data: a dataframe
    :param m: minimum diagonal value (defaults to 0.8)
    :param alpha: the degree of change, from 0 (no changes) to 1 (max changes). Defaults to 0.5
    :param columns: a list of the names of the columns to apply PRAM to. Defaults to None, applying to all columns.
    :return: a dataset modified using the PRAM algorithm
    """
    return Pram.pram(data,m=m, alpha=alpha, columns=columns)


def main():
    argparser = argparse.ArgumentParser(description='Post-randomisation method (PRAM) for Python.')
    argparser.add_argument('input_path', metavar='<input>', type=str, nargs=1, default='input.csv',
                           help='The name of the CSV data file to process')
    argparser.add_argument('output_path', metavar='<output>', type=str, nargs='?', default='output.csv',
                           help='The output file name')
    argparser.add_argument('m', metavar='<m>', type=float, nargs='?', default=0.8,
                           help='The minimum diagonal value')
    argparser.add_argument('a', metavar='<a>', type=float, nargs='?', default=0.5,
                           help='The alpha value')
    argparser.add_argument('-f', action='store_true',
                           help='Print a frequency table showing original vs changed frequencies.')

    args = argparser.parse_args()

    # Defaults
    input_path = vars(args)['input_path'][0]
    output_path = vars(args)['output_path']
    param_minimum = vars(args)['m']
    param_alpha = vars(args)['a']
    print_frequencies = vars(args)['f']

    if not os.path.exists(input_path):
        logging.error('Input data file does not exist')
        exit()
    else:
        logging.info("Input data file: " + input_path)

    logging.info("Output file: " + output_path)

    # Load the dataset
    input_data = pd.read_csv(input_path)

    # Apply the perturbation
    output_data = pram(input_data, m=param_minimum, alpha=param_alpha)

    # Print frequency table
    if print_frequencies:
        Pram.__print_frequencies__(input_data, output_data)

    # Write the output
    output_data.to_csv(output_path, encoding='UTF-8', index=False)


if __name__ == "__main__":
    main()