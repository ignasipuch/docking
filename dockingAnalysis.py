import os
import shutil
import matplotlib.pyplot as plt
from scipy.stats import linregress
import numpy as np
import pandas as pd
import seaborn as sns
import csv
from rdkit import Chem
from rdkit.Chem.Descriptors import ExactMolWt


class DockingAnalyzer:
    """
    Attributes
    ==========
    receptor : str
        Name of the receptor's file (sdf, mol2 or pdb).
    ligands : str
        Name of the file were ligands in a csv with SMILES are located.
    docking_tool : str
        Docking software wanted.
    experimental_data : str
        File containing the experimental data sorted by ligand name.
    calculated_data : str
        File containing the docking data sorted by ligand name.
    molecular_weight : pandas.DataFrame
        Data frame with the molecular weight data.
    protocol : str
        Name of the protocol used.

    Methods
    =======
    glideAnalysis(self, experimental_data, column_name)
        Calculate energetic correlation between Glide's predictions and
        experimental data. Also it plots the distribution of time spent
        per ligand.
    rdockAnalysis(self,  experimental_data, column_name)
        Calculate energetic correlation between rDock's predictions and
        experimental data. 


    Hidden Methods
    ==============
    _correlationPlotter(self, x, y, docking_method)
        Plotts x and y in a z_score format and stores 
        the image.
    _molecularWeightCalculator(self)
        Calculates the molecular weights of the ligands involved
        in the docking.
    _doubleCorrelationPlotter(self, experimental, calculated, molecular_weights, docking_method)
        Makes two plots with three different vectors.
    _glideDockingResultsChecker(self, protocol)
        Checks if the results from the Glide's docking
        are in place. 
    _glideDataFrameRetriever(self)
        Retrieves csv generated by Glide's docking, trims,
        and adds important information.
    _glideTimePlotter(self)
        Plots a histogram with Glide's time data.
    _rdockDockingResultsChecker(self) 
        Checks if the results from the rDock's docking
        are in place.  
    _rdockDataFrameGenerator(self)
        Generates a dataframe with all the important information
        from all the fils generated with the rDock docking.
    _rdockDataFrameTrimmer(self)
        Modifies and trims the original dataframe to obtain the 
        one that we are interested in.
    _correlation(self, experimental_data, column_name)
            Generates the directory to store plots and obtains
            x and y vectors to pass onto _correlationPlotter.
    """

    def __init__(self):
        """
        Initialize object and assign atributes.
        """

        self.receptor = os.listdir('1_input_files/receptor')[0]
        self.ligands = os.listdir('1_input_files/ligands')[0]
        self.docking_tool = None
        self.experimental_data = None
        self.calculated_data = None
        self.molecular_weight = None
        self.protocol = None

    def _correlationPlotter(self, x, y, docking_method, protocol):
        """
        Makes a scatter plot of the two vectors' z-score
        and finds the correlation between them

        Parameters
        ==========
        x : np.array
            Array with the x-axis values
        y : np.array
            Array with the y-axis values
        docking_method : str
            Method with which the values have been obtained.
        """

        # Creating a folder to store plots
        if not os.path.isdir('3_docking_job/images'):
            os.mkdir('3_docking_job/images')

        # Calculate z-scores for x and y
        z_x = (x - np.mean(x)) / np.std(x)
        z_y = (y - np.mean(y)) / np.std(y)

        m_z, n_z, r_z, p_z, _ = linregress(z_x, z_y)

        plt.figure()
        plt.scatter(z_x, z_y)

        # Set labels and title
        plt.xlabel('Z score experimental')
        plt.ylabel('Z score calculated')
        plt.title('{} Z-score correlation'.format(docking_method))
        plt.plot(z_x, m_z*np.array(z_x) + n_z, color='orange',
                 label='r = {:.2f}\np = {:.2f}\nn = {}'.format(r_z, p_z, len(x)))
        plt.legend(loc='best')
        
        if protocol == 'dock':
            plt.savefig(
            '3_docking_job/images/{}_zscore_correlation.png'.format(docking_method), format='png')
        if protocol == 'score':
            plt.savefig(
            '3_docking_job/images/rescoring_{}_zscore_correlation.png'.format(docking_method), format='png')

        m, n, r, p, _ = linregress(x, y)

        plt.figure()
        plt.scatter(x, y)

        # Set labels and title
        plt.xlabel('Experimental')
        plt.ylabel('Calculated')
        plt.title('{} correlation'.format(docking_method))
        plt.plot(x, m*np.array(x) + n, color='orange',
                 label='r = {:.2f}\np = {:.2f}\nn = {}'.format(r, p, len(x)))
        plt.legend(loc='best')

        if protocol == 'dock':
            plt.savefig(
            '3_docking_job/images/{}_correlation.png'.format(docking_method), format='png')
        if protocol == 'score':
            plt.savefig(
            '3_docking_job/images/rescoring_{}_correlation.png'.format(docking_method), format='png')

    def _molecularWeightCalculator(self):
        ''''
        Calculates molecular weights of the ligands to dock and stores the 
        values in a csv.
        '''

        def calculate_molecular_weight(smiles):
            ''''
            Compute the molecular weight per SMILE.

            Parameters
            ==========

            smiles : str
                String with the smiles corresponding to a molecule.
            '''

            mol = Chem.MolFromSmiles(smiles)
            return ExactMolWt(mol)

        path = '1_input_files/molecular_weight'
        path_images = '3_docking_job/images'

        if not os.path.isdir(path_images):
            os.mkdir(path_images)

        if not os.path.isdir(path):
            os.mkdir(path)

        ligand_file = os.listdir('1_input_files/ligands/')[0]
        df = pd.read_csv(os.path.join(
            '1_input_files/ligands/', ligand_file), header=None)

        molecular_weights = df.iloc[:, 0].apply(calculate_molecular_weight)
        new_df = pd.DataFrame(
            {'ligand': df.index, 'molecular_weight': molecular_weights})

        new_df.to_csv(os.path.join(path, 'molecular_weight.csv'))

        self.molecular_weight = new_df

        # Histogram plot
        plt.figure()
        sns.histplot(data=new_df, x='molecular_weight',
                     kde=True, stat='density', alpha=0.5)
        plt.xlabel('MW (Da)')
        plt.ylabel('Density')
        plt.title('MW Distribution')
        plt.savefig('3_docking_job/images/mw_distribution.png', format='png')

    def _doubleCorrelationPlotter(self, experimental, calculated, molecular_weights, docking_method, protocol):
        """
        Makes a scatter plot of the two first vectors against the third with z-score
        and finds the correlation between them.

        Parameters
        ==========
        experimental : np.array
            Array with the experimental scores of the ligands.
        calculated : np.array
            Array with the rdock scores of the ligands.
        molecular_weights : np.array
            Array with molecular weights of the ligands.
        docking_method : str
            Method with which the values have been obtained.
        """

        # Creating a folder to store plots
        if not os.path.isdir('3_docking_job/images'):
            os.mkdir('3_docking_job/images')

        # Calculate z-scores for x and y
        z_mw = (molecular_weights - np.mean(molecular_weights)) / \
            np.std(molecular_weights)
        z_exp = (experimental - np.mean(experimental)) / np.std(experimental)
        z_cal = (calculated - np.mean(calculated)) / np.std(calculated)

        m_exp, n_exp, r_exp, p_exp, _ = linregress(z_mw, z_exp)
        m_cal, n_cal, r_cal, p_cal, _ = linregress(z_mw, z_cal)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Left subplot
        ax1.set_xlabel('Z score MW')
        ax1.set_ylabel('Z score energy')
        ax1.set_title('MW vs experimental: Z-score correlation')
        ax1.scatter(z_mw, z_exp, label='experimental')
        ax1.plot(z_mw, m_exp*np.array(z_mw) + n_exp, color='orange',
                 label='r = {:.2f}\np = {:.2f}\nn = {}'.format(r_exp, p_exp, len(z_mw)))
        ax1.legend(loc='best')

        y_min = min(ax1.get_ylim()[0], ax2.get_ylim()[0])
        y_max = max(ax1.get_ylim()[1], ax2.get_ylim()[1])
        ax1.set_ylim(y_min, y_max)
        ax2.set_ylim(y_min, y_max)

        # Right subplot
        ax2.set_xlabel('Z score MW')
        ax2.set_ylabel('Z score energy')
        ax2.set_title(
            ' MW vs {} score: Z-score correlation'.format(docking_method, docking_method))
        ax2.scatter(z_mw, z_cal, marker='x', color='black',
                    label='{}'.format(docking_method))
        ax2.plot(z_mw, m_cal*np.array(z_mw) + n_cal, color='#a020f0', linestyle=':',
                 label='r = {:.2f}\np = {:.2f}\nn = {}'.format(r_cal, p_cal, len(z_mw)))
        ax2.legend(loc='best')

        # General title for the entire figure
        fig.suptitle('MW vs Energy', fontsize=16)
        plt.tight_layout()
        
        if protocol == 'dock':
            plt.savefig(
            '3_docking_job/images/{}_mw_zscore_correlation.png'.format(docking_method), format='png')
        if protocol == 'score':
            plt.savefig(
            '3_docking_job/images/rescoring_{}_mw_zscore_correlation.png'.format(docking_method), format='png')

    def _glideDockingResultsChecker(self, protocol):
        """
        Checks if the results obtained with glide have been downloaded 
        in the correct path.
        """

        if protocol == 'dock':
            
            path_docking = '3_docking_job/job'
            path_results = os.path.join(
                path_docking, [x for x in os.listdir(path_docking) if x.endswith('.csv')][0])
            
            if not os.path.isfile(path_results):
                raise Exception(
                    'ResultsMissingError: Before initializing the object the results must be downloaded at {}'.format(path_docking))
            
        elif protocol == 'score':
            path_docking = '3_docking_job/glide_score'
            
            paths_to_check = []
            for ligand in [x for x in os.listdir(path_docking) if (x != '.ipynb_checkpoints') and (x != 'glide_score.csv')]:
                path_ligand = os.path.join(path_docking,ligand)
                path_csv = os.path.join(path_ligand,[x for x in os.listdir(path_ligand) if x.endswith('_score.csv')][0])
                paths_to_check.append(path_csv)
        
            if len(paths_to_check) == 0:
                raise Exception(
                    'ResultsMissingError: Before initializing the object the results must be downloaded at {}'.format(path_docking))

        print(' - Glide docking results found')

        self.docking_tool = 'glide'

    def _glideDataFrameRetriever(self, protocol):
        """
        Retrieves the data frame generated with the Glide docking.
        It also modifies certain columns and values to end up
        having a dataframe with the values that we are interested
        in such as SMILES, name of the ligand, ligand number,
        time, and score. It also stores only the best conformation
        per ligand to retrieve the original number of ligands of
        the dataset (since ligprep generates conformers).
        """

        if protocol == 'dock':

            path_docking = '3_docking_job/job'
            path_results = os.path.join(
                path_docking, [x for x in os.listdir(path_docking) if x.endswith('.csv')][0])
            
            # Keeping important columns
            df_og = pd.read_csv(path_results)
            columns_to_keep = ['SMILES', 'title', 'i_i_glide_lignum',
                            'r_glide_cpu_time', 'r_i_docking_score']
            df = df_og[columns_to_keep].copy()

            # Adding molecule number to the dataframe
            prev_title = None
            prev_value = None
            modified_i_i_glide_lignum = np.zeros(df.shape[0], dtype=int)

            for i, row in df.iterrows():
                if row['title'] != prev_title:
                    prev_title = row['title']
                    prev_value = row['i_i_glide_lignum']
                modified_i_i_glide_lignum[i] = row['i_i_glide_lignum'] - prev_value

            df.insert(2, 'conformer', modified_i_i_glide_lignum + 1)

            df.to_csv('3_docking_job/Glide_whole_dataset.csv')

            # Sorting by energies and keeping only one per molecule
            df_csv_sort = df.sort_values(
                'r_i_docking_score').reset_index(drop=True)

            df_result = df_csv_sort.drop_duplicates(['title', 'i_i_glide_lignum'])
            sorted_df = df_result.sort_values(['title', 'i_i_glide_lignum'])

            sorted_df = sorted_df.sort_values('r_i_docking_score')
            sorted_df = sorted_df.drop_duplicates('title')
            sorted_df = sorted_df.sort_values('title')

            sorted_df.to_csv('3_docking_job/Glide_dataset.csv')

            print(' - Csv information imported and sorted (self.calculated_data)')

            self.calculated_data = sorted_df

        elif protocol == 'score':
            path_docking = '3_docking_job/glide_score'
    
            paths_to_check = []
            for ligand in [x for x in os.listdir(path_docking) if (x != '.ipynb_checkpoints') and (x != 'glide_score.csv')]:
                path_ligand = os.path.join(path_docking,ligand)
                path_csv = os.path.join(path_ligand,[x for x in os.listdir(path_ligand) if x.endswith('_score.csv')][0])
                paths_to_check.append(path_csv)

            dfs = []
            for file in paths_to_check:
                df = pd.read_csv(file)
                dfs.append(df)

            merged_df = pd.concat(dfs, ignore_index=True)
            merged_df.to_csv('3_docking_job/glide_score/glide_score.csv')
            self.calculated_data = merged_df

    def _glideTimePlotter(self):
        """
        Makes a histogram plot to show the distribution of times 
        invested in performing the docking.
        """

        df = self.calculated_data

        plt.figure()
        plt.hist(df['r_glide_cpu_time'], bins=10,
                 alpha=0.3, color='blue', density=True)

        kde = sns.kdeplot(df['r_glide_cpu_time'], color='red')

        x_max = kde.get_lines()[0].get_data()[
            0][kde.get_lines()[0].get_data()[1].argmax()]

        plt.axvline(x_max, color='black', linestyle='--',
                    label='Max KDE: {:.2f}'.format(x_max))

        plt.xlabel("Glide's cpu time (s)")
        plt.ylabel("Density")
        plt.title("Glide's time distribution")
        plt.xlim(0, df['r_glide_cpu_time'].max())
        plt.legend()
        plt.savefig(
            '3_docking_job/images/glide_time_distribution.png', format='png')

        print(' - Time distribution figure plotted correctly.')

    def _rdockDockingResultsChecker(self, protocol):
        """
        Checks if the results obtained with rdock have been downloaded 
        in the correct path.

        Parameters
        ==========
        protocol : str
            Protocol used to obtain the outputs to retrieve.
        """

        if protocol == 'dock':

            self.protocol = 'dock'
            self.docking_tool = 'rdock'

            path_docking = '3_docking_job/job/results'
            path_results = [x for x in os.listdir(
                path_docking) if x.endswith('.sd')][0]

            if len(path_results) == 0 and path_results[0].endswith('sd'):
                raise Exception(
                    'ResultsMissingError: Before initializing the object the results must be downloaded and located at {}'.format(path_docking))

        elif protocol == 'score':

            self.protocol = 'score'
            self.docking_tool = 'rdock'

            path_score = '3_docking_job/rdock_score'
            output_files = 0
            input_folders = 0

            for folder in [x for x in os.listdir(path_score) if os.path.isdir(os.path.join(path_score, x))]:
                input_folders += 1
                path_folder_score = os.path.join(path_score, folder)
                for file in os.listdir(path_folder_score):
                    if file == 'ligand_out.sd':
                        output_files += 1

            outputs_per_inputs = output_files/input_folders

            if outputs_per_inputs != 1:
                raise Exception(
                    'OutputError: No tall the simulations have generated an output.')

        else:
            raise Exception(
                'ProtocolError: Only \'dock\' or \'score\' are accepted as protocols.')

    def _rdockDataFrameGenerator(self):
        """
        It generates a dataframe with all the important information
        stored in the multiple files, such as: file name, location index,
        ligand name, conformer, and rdock score.
        """

        if self.protocol == 'dock':

            # Folder path containing the files
            folder_path = '3_docking_job/job/results'
            storage_path = '3_docking_job/'

            data = []

            for filename in [x for x in os.listdir(folder_path) if x.startswith('split')]:
                file_path = os.path.join(folder_path, filename)

                counter = 1
                score_bool = False
                conformer_bool = False

                # Open the file
                with open(file_path, 'r') as file:
                    for line in file:
                        if score_bool:
                            score = line.split()[0]
                        if conformer_bool:
                            ligand, conformer = line.split('-')
                            data.append(
                                [filename, counter, ligand, conformer, score])
                        if '$$$$' in line:
                            counter += 1
                        if '>  <SCORE>' in line:
                            score_bool = True
                        else:
                            score_bool = False
                        if '>  <s_lp_Variant>' in line:
                            conformer_bool = True
                        else:
                            conformer_bool = False

            # Write the extracted data to a CSV file
            output_file = 'rDock_data.csv'
            with open(os.path.join(storage_path, output_file), 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['file_name', 'file_entry', 'ligand',
                                 'conformer', 'rdock_score'])
                writer.writerows(data)

            print(' - rDock data extraction completed.')
            print(' - Data saved in {}'.format(os.path.join(storage_path, output_file)))

        elif self.protocol == 'score':

            # Folder path containing the files
            folder_path = '3_docking_job/rdock_score'
            storage_path = '3_docking_job/'

            data = []

            for filename in [x for x in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, x))]:
                file_path = os.path.join(
                    folder_path, filename, 'ligand_out.sd')

                ligand = filename

                counter = 1
                score_bool = False
                conformer_bool = False

                # Open the file
                with open(file_path, 'r') as file:
                    for line in file:
                        if score_bool:
                            score = line.split()[0]
                            data.append(
                                [filename, counter, ligand, score])
                        if '$$$$' in line:
                            counter += 1
                        if '>  <SCORE>' in line:
                            score_bool = True
                        else:
                            score_bool = False

            # Write the extracted data to a CSV file
            output_file = 'rDock_rescore_data.csv'
            with open(os.path.join(storage_path, output_file), 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    ['file_name', 'file_entry', 'ligand', 'rdock_score'])
                writer.writerows(data)

        print(' - rDock data extraction completed.')
        print(' - Data saved in {}'.format(os.path.join(storage_path, output_file)))

    def _rdockDataFrameTrimmer(self):
        """
        Modifies and trims the rdock dataframe to have only 
        the best score per ligand sorted by name of the ligand
        to end up having the same number of ligands than in the 
        original dataset (since ligprep generates multiple conformers).
        """

        if self.protocol == 'dock':

            # Sorting data
            df = pd.read_csv('3_docking_job/rDock_data.csv')
            sorted_df = df.sort_values('rdock_score')
            unique_df = sorted_df.drop_duplicates('ligand')
            final_df = unique_df.sort_values('ligand')

            # Adding new column with conformer generated.
            final_df['docking_conformation'] = final_df['file_entry'] - \
                ((final_df['file_entry'] - 1) // 50) * 50

            # Reorder the columns
            desired_order = ['ligand', 'conformer', 'docking_conformation',
                             'file_name', 'file_entry', 'rdock_score']
            save_df = final_df.reindex(columns=desired_order)
            save_df.to_csv('3_docking_job/rDock_best_poses.csv', index=False)

            self.calculated_data = final_df

            print(
                ' - Csv generated at 3_docking_job/rDock_best_poses.csv with best poses.')

        elif self.protocol == 'score':

            df = pd.read_csv('3_docking_job/rDock_rescore_data.csv')
            self.calculated_data = df

    def _correlation(self, experimental_data, column_name, protocol):
        """
        Uses _correlationPlotter to plot the calculated vs the
        experimental values of the energies involved in a docking.

        Parameters
        ==========
        experimental_data : str
            Name of the csv file with the experimental data.
        column_name : str
            Name of the column where the data in the csv is stored.
        """

        file_name = experimental_data.split('/')[-1]

        # Move experimental data to input data
        if not os.path.isdir('1_input_files/experimental_energies'):
            os.mkdir('1_input_files/experimental_energies')
            shutil.move(file_name, '1_input_files/experimental_energies/')

        df_experimental = pd.read_csv(os.path.join(
            '1_input_files/experimental_energies/', file_name), index_col=0)
        df_calculated = self.calculated_data
        df_mw = self.molecular_weight

        self.experimental_data = df_experimental

        x = df_experimental[column_name].to_numpy()
        mw = df_mw.iloc[:, 1].to_numpy()

        if self.docking_tool == 'rdock':
            y = df_calculated.rdock_score.to_numpy()
        elif self.docking_tool == 'glide':
            y = df_calculated.r_i_docking_score.to_numpy()

        self._correlationPlotter(x, y, self.docking_tool, protocol)
        self._doubleCorrelationPlotter(x, y, mw, self.docking_tool, protocol)

        print(' - Correlation image generated succesfully')
        print(' - Molecular weight plots generated succesfully.')
        print(' - Images stored at 3_docking_job/images\n')

    def glideAnalysis(self, experimental_data, column_name, protocol='dock'):
        """
        Uses different hidden methods to retrieve all the data 
        from the glide docking simulation and generate an 
        energy correlation plot as well as a histogram of the 
        ditribution of time spent per ligand.

        Parameters
        ==========
        experimental_data : str
            Name of the csv file with the experimental data.
        column_name : str
            Name of the column where the data in the csv is stored.
        protocol : str
            Protocol used to obtain the results retrieved.
        """

        self.protocol = protocol

        self._glideDockingResultsChecker(protocol)
        self._glideDataFrameRetriever(protocol)
        self._molecularWeightCalculator()
        self._correlation(experimental_data, column_name)
        self._glideTimePlotter()

    def rdockAnalysis(self, experimental_data, column_name, protocol='dock'):
        """
        Uses different hidden methods to retrieve all the data 
        from the rdock docking simulation and generate an 
        energy correlation plot.

        Parameters
        ==========
        experimental_data : str
            Name of the csv file with the experimental data.
        column_name : str
            Name of the column where the data in the csv is stored.
        protocol : str
            Protocol used to obtain the results retrieved.
        """

        self._rdockDockingResultsChecker(protocol)
        self._rdockDataFrameGenerator()
        self._rdockDataFrameTrimmer()
        self._molecularWeightCalculator()
        self._correlation(experimental_data, column_name, protocol)

    def rdockOutputToDataFrame(self, path_file, protocol='dock'):
        """
        Reads a single sdf file to obtain all the annotations written for 
        each molecule written in the file and stores the data in a dataframe.

        Parameters
        ==========
        path_file : str
            Path to the sdf file we want to analyze.
        protocol : str
            Protocol used to obtain the results retrieved.

        Returns
        =======

        df : pandas.DataFrame
            Dataframe with all the sdf annotations data.
        """

        def extract_property(mol, prop, default=0):
            """
            Extracts a property value from a molecule and converts it to a float.

            Parameters
            ==========
            mol : RDKit Mol object
                The molecule from which the property will be extracted.
            prop : str
                The name of the property to extract from the molecule.
            default : float, optional
                The default value to return if the property is missing or cannot be
                converted to a float. Default is 0.

            Returns
            =======
            value : float
                The extracted property value as a float. If the property is missing or
                cannot be converted to a float, the default value is returned.
            """
            try:
                return float(mol.GetProp(prop))
            except:
                return default

        # Reading SDF
        supplier = Chem.SDMolSupplier(path_file)
        sdf_dict = {}

        for cont, mol in enumerate(supplier):
            mol_dict = {}

            if mol is not None:
                # Extract properties from the molecule
                molecule_name = mol.GetProp('Name') if protocol == 'dock' else mol.GetProp('Name').split('/')[-2]
                molecule_conformer = mol.GetProp('s_lp_Variant') if protocol == 'dock' else '-'

                properties = [
                    'SCORE', 'SCORE.INTER', 'SCORE.INTER.CONST', 'SCORE.INTER.POLAR',
                    'SCORE.INTER.REPUL', 'SCORE.INTER.ROT', 'SCORE.INTER.VDW',
                    'SCORE.INTRA', 'SCORE.INTRA.DIHEDRAL', 'SCORE.INTRA.DIHEDRAL.0',
                    'SCORE.INTRA.POLAR', 'SCORE.INTRA.POLAR.0', 'SCORE.INTRA.REPUL',
                    'SCORE.INTRA.REPUL.0', 'SCORE.INTRA.VDW', 'SCORE.INTRA.VDW.0',
                    'SCORE.SYSTEM', 'SCORE.SYSTEM.CONST', 'SCORE.SYSTEM.DIHEDRAL',
                    'SCORE.SYSTEM.POLAR', 'SCORE.SYSTEM.REPUL', 'SCORE.SYSTEM.VDW'
                ]

                mol_dict.update({
                    'Name': molecule_name,
                    'Conformer': molecule_conformer,
                    **{prop: extract_property(mol, prop) for prop in properties}
                })

                sdf_dict[cont] = mol_dict

        df = pd.DataFrame.from_dict(sdf_dict, orient="index")
        return df